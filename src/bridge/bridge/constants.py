"""
ファイル名：constants.py

ROS2 bridge パッケージ内の定数を定義するファイル
"""
from typing import Final
from rclpy.qos import QoSProfile

# デバッグフラグ
DEBUG: Final[bool] = True

# トピック名(カメラ画像用)
TOPICNAME_IMAGE: Final[str] = 'camera_image'
# トピック名(Joy用)
TOPICNAME_JOY: Final[str] = 'joy'

# QoS設定
QOS_PROFILE: Final[QoSProfile] = QoSProfile(depth=10)

# カメラ画像エンコーディングタイプ
IMAGE_ENCODING_TYPE: Final[str] = 'bgr8'
#カメラデバイスの番号(/dev/videoX の X 部分)
CAMERA_DEV_LETTER: Final[int] = 0  # /dev/video0
#CAMERA_DEV_LETTER: Final[int] = 1  # /dev/video1


# ゲームパッドデバイスの番号(/dev/input/jsX の X 部分)
GAMEPAD_DEV_LETTER: Final[int] = 0  # /dev/input/js0
#GAMEPAD_DEV_LETTER: Final[int] = 1  # /dev/input/js1

# ゲームパッド入力チェックの間隔
GAMEPAD_CHECK_INTERVAL_SEC: Final[float] = 0.1  # ゲームパッド入力チェックの間隔(秒)

# ゲームパッドアナログ値変化有無を判断する閾値
GAMEPAD_ANALOG_CHANGE_THRESHOLD: Final[float] = 0.05

# Publish間隔(秒)
PUBLISH_INTERVAL_SEC: Final[float] = 0.05

# HTTP 通信のタイムアウト時間(秒)
HTTP_TIMEOUT_SEC: Final[float] = 1.0

# テレメトリ平均化対象の時間幅(ミリ秒)
TELEMETRY_WINDOW_MSEC: Final[int] = 100


# ROBOBIKE IPアドレス
ROBOBIKE_DEFAULT_IP: Final[str] = "192.168.4.1" # 実機
ROBOBIKE_DUMMY_IP: Final[str]   = "127.0.0.1:8080" # ダミー

# ROBOBIKE GET コマンド用の URL プレフィックス/サフィックス
ROBOBIKE_COMMAND_PREFIX: Final[str] = "/command?button=" # command送信(ボタン番号 1以上)
ROBOBIKE_VALUE_SUFFIX: Final[str] = "&value=" # ROBOBIKE 操舵値(int)(100,-100)
ROBOBIKE_GET_ACC_PREFIX: Final[str] = "/get_acc" # ROBOBIKE テレメトリCSV(複数行)取得
ROBOBIKE_CLEAR_BUFFER_PREFIX: Final[str] = "/clear_buffer" # ROBOBIKE テレメトリクリア

"""ROBOBIKE コマンド名リスト"""
ROBOBIKE_COMMAND_NAMES: Final[list[str]] = [
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
ROBOBIKE_COMMAND_NAMES_LEN: Final[int] = len(ROBOBIKE_COMMAND_NAMES)

"""
コマンド名をインデックス番号に変換する

Args:
    button (str): コマンド名(ROBOBIKE_COMMAND_NAMES に含まれるいずれかの要素)。

Returns:
    int: コマンド名に対応するインデックス番号(1,2,3,...)
"""
def get_command_index(button: str) -> int:
    if button not in ROBOBIKE_COMMAND_NAMES:
        raise ValueError(f"Invalid button name: {button}")
    return ROBOBIKE_COMMAND_NAMES.index(button) + 1

"""
コマンド番号をコマンド名に変換する

Args:
    index (int): コマンド番号(1,2,3,...)。

Returns:
    str: コマンド番号に対応するコマンド名。
"""
def get_command_name(index: int) -> str:
    if index < 1 or index > ROBOBIKE_COMMAND_NAMES_LEN:
        raise ValueError(f"Invalid command index: {index}")
    return ROBOBIKE_COMMAND_NAMES[index - 1]


"""ROBOBIKE ステータス CSV インデックスリスト(すべて)"""
ROBOBIKE_STATUS_CSV_INDEXES: Final[list[str]] = [
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
ROBOBIKE_STATUS_CSV_INDEXES_LEN: Final[int] = len(ROBOBIKE_STATUS_CSV_INDEXES)

"""ROBOBIKE ステータス CSV インデックスリスト(float値をとるもの)"""
ROBOBIKE_STATUS_CSV_INDEXES_FLOAT: Final[list[str]] = [
    "gain_str",          # ステアリングゲイン(例:0.030)
    "gain_w_roll",       # ロール方向のゲイン(例:12.000)
    "gain_str_diff",     # ステアリング差分ゲイン(例:0.030)
    "yaw_coeff",         # ヨー係数(例:0.011)
    "str_cmd_rate",      # ステアリングコマンドレート(例:0.000)
    "auto_circ_gain"     # 自動旋回ゲイン(例:0.750)
]
ROBOBIKE_STATUS_CSV_INDEXES_FLOAT_LEN: Final[int] = len(ROBOBIKE_STATUS_CSV_INDEXES_FLOAT)

"""ROBOBIKE ステータス CSV インデックスリスト(int値をとるもの)"""
ROBOBIKE_STATUS_CSV_INDEXES_INT: Final[list[str]] = [
    "PROGVER",           # Robobike実機プログラムのバージョン
    "DATAVER",           # Robobike実機プログラムの取り扱うデータのバージョン
    "str0",              # ステアリング角度の初期値(例:0)
    "mot_spd",           # モーター速度(例:10)
    "ang_std_nut",       # 標準ナット角度(例:20)
    "str_turn",          # ステアリングターン角度(例:40)
    "autoCircling",      # 自動旋回モード(例:0 or 1)
    "str_cmd_speed",     # ステアリングコマンド速度(例:30)
    "doSweep"            # スイープ動作(例:0)
]
ROBOBIKE_STATUS_CSV_INDEXES_INT_LEN: Final[int] = len(ROBOBIKE_STATUS_CSV_INDEXES_INT)

"""
ステータス名をインデックス番号に変換する

Args:
    status (str): ステータス名(ROBOBIKE_STATUS_CSV_INDEXES に含まれるいずれかの要素)。

Returns:
    int: ステータス名に対応するインデックス番号(0,1,2,...)
"""
def get_status_index(status: str) -> int:
    if status not in ROBOBIKE_STATUS_CSV_INDEXES:
        raise ValueError(f"Invalid status name: {status}")
    return ROBOBIKE_STATUS_CSV_INDEXES.index(status)

"""
ステータスインデックス番号をステータス名に変換する

Args:
    index (int): ステータスインデックス番号(0,1,2,...)。

Returns:
    str: インデックス番号に対応するステータス名。
"""
def get_status_name(index: int) -> str:
    if index < 0 or index >= len(ROBOBIKE_STATUS_CSV_INDEXES):
        raise ValueError(f"Invalid status index: {index}")
    return ROBOBIKE_STATUS_CSV_INDEXES[index]

"""ROBOBIKE テレメトリ CSV インデックスリスト(すべて)"""
ROBOBIKE_TELEMETRY_CSV_INDEXES: Final[list[str]] = [
    "a",
    "time",
    "drv",
    "str",
    "std",
    "swp_sg",
    "sv_pos",
    "gy_roll",
    "gy_yaw",
    "gy_pitch",
    "acc_x",
    "acc_y",
    "acc_z"
]
ROBOBIKE_TELEMETRY_CSV_INDEXES_LEN: Final[int] = len(ROBOBIKE_TELEMETRY_CSV_INDEXES)

"""ROBOBIKE テレメトリ CSV インデックスリスト(float値をとるもの)"""
ROBOBIKE_TELEMETRY_CSV_INDEXES_FLOAT: Final[list[str]] = [
    "drv",
    "str",
    "std",
    "swp_sg",
    "sv_pos",
    "gy_roll",
    "gy_yaw",
    "gy_pitch",
    "acc_x",
    "acc_y",
    "acc_z"
]
ROBOBIKE_TELEMETRY_CSV_INDEXES_FLOAT_LEN: Final[int] = len(ROBOBIKE_TELEMETRY_CSV_INDEXES_FLOAT)

"""ROBOBIKE テレメトリ CSV インデックスリスト(int値をとるもの)"""
ROBOBIKE_TELEMETRY_CSV_INDEXES_INT: Final[list[str]] = [
    "time"
]
ROBOBIKE_TELEMETRY_CSV_INDEXES_INT_LEN: Final[int] = len(ROBOBIKE_TELEMETRY_CSV_INDEXES_INT)