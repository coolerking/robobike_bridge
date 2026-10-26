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
    "stp_all",          # Robobike 全停止
    "only_data",        # データ取得のみ
    "bt_F",             # FORWARDボタンを押したときのコマンド
    "bt_S",             # STOPボタンを押したときのコマンド
    "bt_L",             # LEFTボタンを押したときのコマンド
    "bt_R",             # RIGHTボタンを押したときのコマンド
    "bt_Str_S",         # ステアリング値を送信するコマンド(valueで (-100<LEFT>, 100<RIGHT>)の範囲で指定)
    "bt_BK",            # BACKボタンを押したときのコマンド
    "bt_A_Up_0",
    "bt_A_Dn_0",
    "bt_A_Up",
    "bt_A_Dn",
    "bt_A_L",
    "bt_A_R",
    "bt_S_Up",
    "bt_S_Dn",
    "bt_R_Up",
    "bt_R_Dn",
    "bt_D_St",
    "bt_D_Up",
    "bt_D_Dn",
    "bt_Std_nutAuto",
    "bt_Std_nutUp",
    "bt_Std_nutDn",
    "bt_str_turnUp",
    "bt_str_turnDn",
    "bt_strcmd_Up",
    "bt_strcmd_Dn",
    "IR_ON",
    "IR_OFF",
    "bt_yaw_coeffUp",
    "bt_yaw_coeffDn",
    "bt_Ld_Default"
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
