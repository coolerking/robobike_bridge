#!/usr/bin/env python3
"""
ファイル名：dummybike.py

Robobike 実機がない場合に使用する、ダミーROBOBIKEモジュール

使い方：
    ros2 run bridge dummybike            # リクエストごとのログなし
    ros2 run bridge dummybike --verbose  # リクエストごとにログを出力
    python3 dummybike.py [--verbose]     # ROS2を使わず直接起動する場合
"""

import copy
import time
import argparse
import threading
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# /get_acc で返すテレメトリのサンプリング周期(ミリ秒)
ACC_SAMPLE_INTERVAL_MSEC = 4
# /get_acc 1回で返す最大行数
ACC_MAX_ROWS = 25
# サーバ起動時刻(テレメトリの time 算出用)
_START_TIME = time.monotonic()
# リクエストごとのログを出力するか(--verbose で有効化)
VERBOSE = False

# ボタン番号の有効範囲(constants.ROBOBIKE_COMMAND_NAMES の 1〜37)
BUTTON_MIN = 1
BUTTON_MAX = 37

# ステータスの初期値(bt_Ld_Default でこの値に戻る)
# 単体でも起動できるよう constants.py は import せず、同じ並びをここに持つ
DEFAULT_STATUS = {
    'PROGVER': 1042,
    'DATAVER': 6,
    'str0': 0,
    'mot_spd': 20,
    'gain_str': 0.030,
    'gain_w_roll': 12.000,
    'gain_str_diff': 0.030,
    'ang_std_nut': 20,
    'str_turn': 40,
    'yaw_coeff': 0.011,
    'autoCircling': 1,
    'str_cmd_rate': 0.000,
    'str_cmd_speed': 30,
    'auto_circ_gain': 0.750,
    'doSweep': 0,
}

# パラメータを増減するボタン: ボタン番号 -> (項目名, 増減値)
BUTTON_ADJUSTMENTS = {
    9: ('mot_spd', 1),            # bt_A_Up_0
    10: ('mot_spd', -1),          # bt_A_Dn_0
    11: ('mot_spd', 1),           # bt_A_Up
    12: ('mot_spd', -1),          # bt_A_Dn
    13: ('str0', -1),             # bt_A_L
    14: ('str0', 1),              # bt_A_R
    15: ('gain_str', 0.01),       # bt_S_Up
    16: ('gain_str', -0.01),      # bt_S_Dn
    17: ('gain_w_roll', 1.0),     # bt_R_Up
    18: ('gain_w_roll', -1.0),    # bt_R_Dn
    20: ('gain_str_diff', 0.01),  # bt_D_Up
    21: ('gain_str_diff', -0.01), # bt_D_Dn
    23: ('ang_std_nut', 1),       # bt_Std_nutUp
    24: ('ang_std_nut', -1),      # bt_Std_nutDn
    25: ('str_turn', 1),          # bt_str_turnUp
    26: ('str_turn', -1),         # bt_str_turnDn
    27: ('str_cmd_speed', 1),     # bt_strcmd_Up
    28: ('str_cmd_speed', -1),    # bt_strcmd_Dn
    31: ('yaw_coeff', 0.01),      # bt_yaw_coeffUp
    32: ('yaw_coeff', -0.01),     # bt_yaw_coeffDn
    35: ('auto_circ_gain', 0.01), # bt_autoCirc_Up
    36: ('auto_circ_gain', -0.01),# bt_autoCirc_Dn
}
# 項目を固定値にするボタン: ボタン番号 -> (項目名, 設定値)
BUTTON_SETTINGS = {
    33: ('doSweep', 1),           # bt_sweepON
    34: ('doSweep', 0),           # bt_sweepOFF
}
# 初期値に戻すボタン
BUTTON_LOAD_DEFAULT = 37          # bt_Ld_Default


class DummyBikeHandler(BaseHTTPRequestHandler):
    """
    ダミーROBOBIKEサーバのリクエストハンドラクラス

    ThreadingHTTPServer でリクエストごとに別スレッドから呼ばれるため、
    クラス変数の状態は _lock で保護する。
    """
    # 状態保護用のロック
    _lock = threading.Lock()
    # 現在のステータス(ボタン操作で変化する)
    status = copy.deepcopy(DEFAULT_STATUS)
    # 前回 /get_acc で返した最終行の time(ミリ秒)
    last_acc_time = None

    def log_message(self, format, *args):
        """
        標準のアクセスログ出力を抑止する(--verbose 指定時のみ出力)
        """
        if VERBOSE:
            super().log_message(format, *args)

    def _send_text(self, body: str, content_type: str, code: int = 200) -> None:
        """
        レスポンスを送信する

        Args:
            body (str): レスポンス本文
            content_type (str): Content-type ヘッダ値(charset は utf-8 固定)
            code (int): HTTPステータスコード
        """
        data = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-type', f'{content_type}; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @classmethod
    def _apply_button(cls, query_params: dict) -> bool:
        """
        ボタン番号に応じてステータスを更新する(_lock 取得済みで呼ぶこと)

        Args:
            query_params (dict): parse_qs で得たクエリパラメータ

        Returns:
            bool: ボタン番号が有効なら True、不正なら False
        """
        try:
            button = int(query_params.get('button', [''])[0])
        except ValueError:
            return False
        if not BUTTON_MIN <= button <= BUTTON_MAX:
            return False

        if button in BUTTON_ADJUSTMENTS:
            name, delta = BUTTON_ADJUSTMENTS[button]
            cls.status[name] += delta
        elif button in BUTTON_SETTINGS:
            name, value = BUTTON_SETTINGS[button]
            cls.status[name] = value
        elif button == BUTTON_LOAD_DEFAULT:
            cls.status = copy.deepcopy(DEFAULT_STATUS)
        # 上記以外(走行・停止・データ取得など)はステータスを変えない
        return True

    @classmethod
    def _get_status_csv(cls, ok: bool) -> str:
        """
        現在のステータスをCSV文字列で生成する(_lock 取得済みで呼ぶこと)

        Args:
            ok (bool): コマンドが受理されたか(False の場合 OK 欄を "NG" にする)
        """
        s = cls.status
        return ",".join([
            "b",
            str(s['PROGVER']),
            str(s['DATAVER']),
            "OK" if ok else "NG",
            str(s['str0']),
            str(s['mot_spd']),
            f"{s['gain_str']:.3f}",
            f"{s['gain_w_roll']:.3f}",
            f"{s['gain_str_diff']:.3f}",
            str(s['ang_std_nut']),
            str(s['str_turn']),
            f"{s['yaw_coeff']:.3f}",
            str(s['autoCircling']),
            f"{s['str_cmd_rate']:.3f}",
            str(s['str_cmd_speed']),
            f"{s['auto_circ_gain']:.3f}",
            str(s['doSweep']),
        ])

    @classmethod
    def _get_acc_csv(cls) -> str:
        """
        前回取得以降の新しいテレメトリ行をCSV文字列で生成する(_lock 取得済みで呼ぶこと)

        time はサーバ起動からの経過ミリ秒とし、ACC_SAMPLE_INTERVAL_MSEC 間隔で
        最大 ACC_MAX_ROWS 行を返す。新しい行がない場合は空文字列を返す。
        """
        now_ms = int((time.monotonic() - _START_TIME) * 1000)
        if cls.last_acc_time is None:
            start_ms = now_ms - ACC_SAMPLE_INTERVAL_MSEC * (ACC_MAX_ROWS - 1)
        else:
            start_ms = cls.last_acc_time + ACC_SAMPLE_INTERVAL_MSEC
        # 返却行数の上限を超える古い行は捨てる
        start_ms = max(start_ms, now_ms - ACC_SAMPLE_INTERVAL_MSEC * (ACC_MAX_ROWS - 1))
        rows = []
        for t in range(start_ms, now_ms + 1, ACC_SAMPLE_INTERVAL_MSEC):
            rows.append(
                f"a,{t},0.000,0.000,36.000,0.000,-61.479,0.269,0.074,0.074,-0.736,-1.296,-9.644"
            )
            cls.last_acc_time = t
        return "\n".join(rows)

    def do_GET(self):
        """
        GETメッセージを処理し、エンドポイントに応じたデータを返す
        """
        # URLをパスとクエリ（?以降の部分）に分解
        parsed_url = urlparse(self.path)
        # クエリパラメータを辞書形式に変換
        query_params = parse_qs(parsed_url.query)
        if VERBOSE:
            print(f"[DummyBikeHandler] {parsed_url.path} query_params: {query_params}")

        if parsed_url.path == '/command':
            # ボタンに応じてステータスを更新し、更新後のステータスを返す
            with DummyBikeHandler._lock:
                ok = DummyBikeHandler._apply_button(query_params)
                body = DummyBikeHandler._get_status_csv(ok)
            self._send_text(body, 'text/csv')
        elif parsed_url.path == '/get_acc':
            with DummyBikeHandler._lock:
                body = DummyBikeHandler._get_acc_csv()
            self._send_text(body, 'text/csv')
        elif parsed_url.path == '/clear_buffer':
            self._send_text("OK", 'text/plain')
        else:
            # 条件に一致しないアクセス（別のURLなど）の場合は 404 Not Found を返す
            self._send_text("Not Found", 'text/plain', code=404)


def run_dummy_bike():
    """
    ダミーROBOBIKEサーバを起動する

    Ctrl+C を押すと終了します。
    """
    global VERBOSE
    parser = argparse.ArgumentParser(
        prog="dummybike",
        description="Dummy ROBOBIKE HTTP server"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print a log line for every request')
    args, _ = parser.parse_known_args()
    VERBOSE = args.verbose

    port = 8080
    server_address = ('', port)

    # サーバーのインスタンスを作成(リクエストごとにスレッドで処理)
    httpd = ThreadingHTTPServer(server_address, DummyBikeHandler)
    print(f"テスト用ダミーサーバを起動しました。ポート番号: {port}")
    print(f"テストURL: http://localhost:{port}/command?..")

    try:
        print("Ctrl+Cで停止できます。")
        # サーバーを実行（Ctrl+Cで停止するまで動き続ける）
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバを停止します。")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_dummy_bike()
