#!/usr/bin/env python3
"""
ファイル名: robobike.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth のWiFi 接続された
Robobike との通信をブリッジするためのモジュールです。

実行例（テストのみ）：
    python3 robobike.py --test # ダミーデータでの実行
    python3 robobike.py # 実機データでの実行
"""
import json
import argparse
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# HTTP 通信のタイムアウト時間(秒)
HTTP_TIMEOUT_SEC = 1.0

# Robobike 本番機 接続用のデフォルト設定
ROBOBIKE_DEFAULT_IP = "192.168.4.1"
ROBOBIKE_COMMAND_PREFIX = "/command?button="
ROBOBIKE_VALUE_SUFFIX = "&value="
ROBOBIKE_COMMAND_NAMES = [
    "stp_all",          #  1: Robobike 全停止
    "only_data",        #  2: データ取得のみ
    "bt_F",             #  3: 10秒直進
    "bt_S",             #  4: 停止
    "bt_L",             #  5: 停止したまま左一杯
    "bt_R",             #  6: 停止したまま右一杯
    "bt_Str_S",         #  7: ステアリング値を送信するコマンド(valueで (-100<LEFT>, 100<RIGHT>)の範囲で指定)
    "bt_BK",            #  8: 連続後進
    "bt_A_Up_0",        #  9: モータ速度(mot_std)+1
    "bt_A_Dn_0",        # 10: モータ速度(mot_std)-1
    "bt_A_Up",          # 11: モータ速度(mot_std)+1で連続前進(ステアリング角維持)
    "bt_A_Dn",          # 12: モータ速度(mot_std)-1で連続前進(ステアリング角維持)
    "bt_A_L",           # 13: ステアリング標準位置(str0)-1
    "bt_A_R",           # 14: ステアリング標準位置(str0)+1
    "bt_S_Up",          # 15: ステアリング感度(gain_str)+0.01
    "bt_S_Dn",          # 16: ステアリング感度(gain_str)-0.01
    "bt_R_Up",          # 17: ロール方向のゲイン(gain_w_roll)+1.00
    "bt_R_Dn",          # 18: ロール方向のゲイン(gain_w_roll)-1.00
    "bt_D_St",          # 19: 停止(mod_spd維持)
    "bt_D_Up",          # 20: ステアリング差分感度(gain_str_diff)+0.01
    "bt_D_Dn",          # 21: ステアリング差分感度(gain_str_diff)-0.01
    "bt_Std_nutAuto",   # 22: 初期傾斜角を標準位置に戻す(停止)
    "bt_Std_nutUp",     # 23: 初期傾斜角(ang_str_nut)+1
    "bt_Std_nutDn",     # 24: 初期傾斜角(ang_str_nut)-1
    "bt_str_turnUp",    # 25: ステアリング最大角(str_turn)+1
    "bt_str_turnDn",    # 26: ステアリング最大角(str_turn)-1
    "bt_strcmd_Up",     # 27: ステアリングコマンド速度(str_cmd_speed)+1
    "bt_strcmd_Dn",     # 28: ステアリングコマンド速度(str_cmd_speed)-1
    "IR_ON",            # 29: 赤外線センサーON
    "IR_OFF",           # 30: 赤外線センサーOFF
    "bt_yaw_coeffUp",   # 31: ヨー係数(yaw_coeff)+0.01
    "bt_yaw_coeffDn",   # 32: ヨー係数(yaw_coeff)-0.01
    "bt_sweepON",       # 33: スイープ動作開始：ステアリングがだんだん激しく小刻みに動く→しばらく動いたら停止
    "bt_sweepOFF",      # 34: スイープ動作停止
    "bt_autoCirc_Up",   # 35: 自動旋回モードのゲイン(auto_circ_gain)を上げる+0.01
    "bt_autoCirc_Dn",   # 36: 自動旋回モードのゲイン(auto_circ_gain)を下げる-0.01
    "bt_Ld_Default"     # 37: ロードデフォルト設定
]

ROBOBIKE_RESPONSE_CSV_INDEXES_V6 = [
    "b",                 # 固定 "b"が必ず帰る
    "PROGVER",           # Robobike実機プログラムのバージョン
    "DATAVER",           # Robobike実機プログラムの取り扱うデータのバージョン
    "OK",                # コマンドが正常に実行されたかどうか、正常時"OK"が返る
    "str0",              # ステアリング角度の初期値(例:0)
    "mot_spd",           # モーター速度(例:10)
    "gain_str",          # ステアリングゲイン(例:0.030)
    "gain_w_roll",       # ロール方向のゲイン(例:12.000)
    "gain_str_diff",     # ステアリング差分ゲイン(例:0.030)
    "ang_std_nut",       # 標準ナット角度(例:20)
    "str_turn",          # ステアリングターン角度(例:40)
    "yaw_coeff",         # ヨー係数(例:0.011)
    "autoCircling",      # 自動旋回モード(例:0 or 1)
    "str_cmd_rate",      # ステアリングコマンドレート(例:0.000)
    "str_cmd_speed",     # ステアリングコマンド速度(例:30)
    "auto_circ_gain",    # 自動旋回ゲイン(例:0.750)
    "doSweep"            # スイープ動作(例:0)
]

class RobobikeBridge():
    """
    Robobike 本番機とHTTP GET通信を行い、コマンド送信を行うためのブリッジクラス。
    """
    def __init__(self, default_ip=ROBOBIKE_DEFAULT_IP) -> None:
        """
        初期化メソッド。

        Args:
            default_ip (str, optional): Robobike の IP アドレス。指定しない場合はデフォルトの IP アドレスを使用。
        """
        self.robobike_base_url = f"http://{default_ip}"

    def _get_command_url(self, button:str='only_data', value:float=None) -> str:
        """
        Robobike 本番機へのコマンド URL を生成します。

        Args:
            button (str): コマンド名(ROBOBIKE_COMMAND_NAMES に含まれるいずれかの要素)。デフォルトは 'only_data'。
            value (float, optional): ボタンに対応する値。指定しない場合は None。

        Returns:
            str: 生成されたコマンド URL。
        """
        # 不正なコマンド名の場合、例外を発生させる
        if not button in ROBOBIKE_COMMAND_NAMES:
            raise ValueError(f"Invalid button name: {button}")

        # button に入っている文字列の配列インデックスを取得
        button_index = ROBOBIKE_COMMAND_NAMES.index(button)

        # コマンド URL を生成(value指定ありの場合はGETパラメータに追加する)
        url = f"{self.robobike_base_url}{ROBOBIKE_COMMAND_PREFIX}{button_index + 1}"
        if value is not None:
            url += f"{ROBOBIKE_VALUE_SUFFIX}{value}"

        return url

    def send_command(self, button:str='only_data', value:float=None) -> dict:
        """
        Robobike 本番機にコマンドを送信します。

        Args:
            button (str): コマンド名(ROBOBIKE_COMMAND_NAMES に含まれるいずれかの要素)。デフォルトは 'only_data'。
            value (float, optional): ボタンに対応する値。指定しない場合は None。

        Returns:
            dict: 成功時はレスポンス情報、失敗時は 'status' と 'error' を含む辞書。
        """
        url = self._get_command_url(button, value)
        try:
            with urlopen(url, timeout=HTTP_TIMEOUT_SEC) as response:
                csv_str = response.read().decode('utf-8')
                print(csv_str)
                # CSV をパースしてリストに変換
                csv_list = csv_str.strip().split(',')
                print(csv_list)
                csv_dict = {}
                if len(csv_list) == len(ROBOBIKE_RESPONSE_CSV_INDEXES_V6):
                    for i in range(len(csv_list)):
                        index = ROBOBIKE_RESPONSE_CSV_INDEXES_V6[i]
                        value = csv_list[i]
                        print(index)
                        print(value)
                        csv_dict[index] = value
                        #csv_dict[index] = float(value) for value in csv_list
                    if csv_dict.get('OK', '').strip() != 'OK':
                        return {
                            'status': 'error',
                            'error': (
                                'Robobike reported command failure: '
                                f"OK={csv_dict.get('OK', '')!r}"
                            ),
                        }
                    return csv_dict
                else:
                    return {
                        'status': 'error',
                        'error': (
                            f'Unexpected response field count: {len(csv_list)} '
                            f'(expected {len(ROBOBIKE_RESPONSE_CSV_INDEXES_V6)})'
                        ),
                    }

        except (HTTPError, URLError, TimeoutError) as e:
            return {'status': 'error', 'error': str(e)}



def test_robobike_bridge():
    parser = argparse.ArgumentParser(
        prog="pub_robobike",
        description="Publish data from a WiFi-connected ROBOBIKE"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Use dummy data instead of real ROBOBIKE data')
    args = parser.parse_args()
    if args.test:
        default_ip = "127.0.0.1:8080"
    else:
        default_ip = ROBOBIKE_DEFAULT_IP
    print(f'Using default IP: {default_ip}')
    bridge = RobobikeBridge(default_ip=default_ip)
    csv_dict = bridge.send_command()
    print(json.dumps(csv_dict, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    test_robobike_bridge()
