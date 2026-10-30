"""
ファイル名：constants.py

ROS2 bridge パッケージ内の定数を定義するファイル
"""
import os
from pathlib import Path
from typing import Final
from rclpy.qos import QoSProfile
from rclpy.qos import qos_profile_sensor_data

# デバッグフラグ
DEBUG: Final[bool] = True

# トピック名(カメラ画像用、JPEG圧縮した sensor_msgs/CompressedImage)
TOPICNAME_IMAGE: Final[str] = 'camera_image/compressed'
# トピック名(Joy用)
#TOPICNAME_JOY: Final[str] = 'joy'
# トピック名(ROBOBIKE /command)
TOPICNAME_ROBOBIKE_COMMAND: Final[str] = 'robobike_command'
# トピック名(ROBOBIKE /status)
TOPICNAME_ROBOBIKE_STATUS: Final[str] = 'robobike_status'
# トピック名(ROBOBIKE /get_acc)
TOPICNAME_ROBOBIKE_TELEMETRY: Final[str] = 'robobike_telemetry'
# トピック名(方策ハートビート、std_msgs/Header)
TOPICNAME_POLICY_HEARTBEAT: Final[str] = 'robobike_policy_heartbeat'
# トピック名(学習データ収集用エピソード開始/終了イベント、std_msgs/String の JSON)
TOPICNAME_ROBOBIKE_EPISODE: Final[str] = 'robobike_episode'

# エピソードイベント種別(robobike_episode の "event" の値)
EPISODE_EVENT_START: Final[str] = 'start'
EPISODE_EVENT_END: Final[str] = 'end'


# QoS設定
QOS_PROFILE: Final[QoSProfile] = QoSProfile(depth=10)

# 方策ハートビート用QoS設定(BEST_EFFORT：遅れて再送されたハートビートは意味がないため)
HEARTBEAT_QOS_PROFILE: Final[QoSProfile] = qos_profile_sensor_data
# 方策の制御周期(秒)：ROBOBIKEのHTTP往復(約80ms)に合わせて10Hz、ハートビートもこの周期で送る
POLICY_CONTROL_INTERVAL_SEC: Final[float] = 0.1
# ウォッチドッグのデフォルトタイムアウト(秒)：この時間ハートビートが途絶えたら緊急停止する
WATCHDOG_DEFAULT_TIMEOUT_SEC: Final[float] = 0.5
# 方策入力(画像・テレメトリ・ステータス)の有効期間(秒)：これより古い入力しかない場合は推論しない
POLICY_INPUT_TIMEOUT_SEC: Final[float] = 0.5
# 方策が前回送信値からこの値(-100〜100 の単位)以上変化した場合のみ操舵コマンドを送信する
POLICY_STEER_CHANGE_THRESHOLD: Final[int] = 5
# ACT が予測した行動列のうち、次の推論までに実行するステップ数(10 = 1秒分)
POLICY_DEFAULT_N_ACTION_STEPS: Final[int] = 10

# カメラ画像用QoS設定(BEST_EFFORT：WiFi越しに1枚落ちても再送せず次のフレームを待つ)
IMAGE_QOS_PROFILE: Final[QoSProfile] = qos_profile_sensor_data

# カメラ画像エンコーディングタイプ(JPEG圧縮前/展開後のOpenCV画像)
IMAGE_ENCODING_TYPE: Final[str] = 'bgr8'
# カメラ画像の配信サイズ(WiFi帯域に収めるため縮小する)
IMAGE_WIDTH: Final[int] = 320
IMAGE_HEIGHT: Final[int] = 240
# カメラ画像のJPEG圧縮形式・品質(0-100)
IMAGE_COMPRESSED_FORMAT: Final[str] = 'jpeg'
IMAGE_JPEG_QUALITY: Final[int] = 80
# カメラ画像のPublish間隔(秒)：ROBOBIKEのHTTP往復(約80ms)に合わせて10Hz
IMAGE_PUBLISH_INTERVAL_SEC: Final[float] = 0.1
# カメラ画像の frame_id
IMAGE_FRAME_ID: Final[str] = 'overhead_camera'
#カメラデバイスの番号(/dev/videoX の X 部分)
CAMERA_DEV_LETTER: Final[int] = 0  # /dev/video0
#CAMERA_DEV_LETTER: Final[int] = 1  # /dev/video1


# Publish間隔(秒)
PUBLISH_INTERVAL_SEC: Final[float] = 0.05

# HTTP 通信のタイムアウト時間(秒)
HTTP_TIMEOUT_SEC: Final[float] = 1.0

# テレメトリ平均化対象の時間幅(ミリ秒)
TELEMETRY_WINDOW_MSEC: Final[int] = 100


# 学習データ・ログ・モデルの保存先ルート(環境変数 ROBOBIKE_DATA_DIR で上書き可)
DATA_ROOT_ENV_NAME: Final[str] = 'ROBOBIKE_DATA_DIR'
DATA_ROOT: Final[Path] = Path(
    os.environ.get(DATA_ROOT_ENV_NAME, Path.home() / 'robobike_data')
).expanduser().resolve()
# 収集データ(ros2 bag 等、未加工のまま保存)
DATA_RAW_DIR: Final[Path] = DATA_ROOT / 'raw'
# 変換後の学習用データセット
DATA_DATASETS_DIR: Final[Path] = DATA_ROOT / 'datasets'
# 学習1回ごとのログ・checkpoint・設定
DATA_RUNS_DIR: Final[Path] = DATA_ROOT / 'runs'
# 推論用に書き出した学習済みモデル
DATA_MODELS_DIR: Final[Path] = DATA_ROOT / 'models'

# ros2 bag で記録するトピック(学習データ収集用)
RECORD_TOPICS: Final[list[str]] = [
    TOPICNAME_IMAGE,
    TOPICNAME_ROBOBIKE_STATUS,
    TOPICNAME_ROBOBIKE_TELEMETRY,
    TOPICNAME_ROBOBIKE_COMMAND,
    TOPICNAME_ROBOBIKE_EPISODE,
]
# ros2 bag の保存形式
RECORD_STORAGE_ID: Final[str] = 'mcap'


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
    "bt_A_Up_0",        #  9: モータ速度(mot_spd)+1
    "bt_A_Dn_0",        # 10: モータ速度(mot_spd)-1
    "bt_A_Up",          # 11: モータ速度(mot_spd)+1で連続前進(ステアリング角維持)
    "bt_A_Dn",          # 12: モータ速度(mot_spd)-1で連続前進(ステアリング角維持)
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

# value値を必要とするコマンド名リスト
ROBOBIKE_COMMAND_NAMES_REQUIRING_VALUE: Final[list[str]] = [
    "bt_Str_S",
]
# value値を必要とするコマンド名リスト長
ROBOBIKE_COMMAND_NAMES_REQUIRING_VALUE_LEN: Final[int] = len(ROBOBIKE_COMMAND_NAMES_REQUIRING_VALUE)
# value値(操舵値)の範囲(整数に丸めてこの範囲に収める)
ROBOBIKE_VALUE_MIN: Final[int] = -100
ROBOBIKE_VALUE_MAX: Final[int] = 100

# 緊急停止コマンド名(ゲームパッド切断・Publish停止・ノード終了時に送信する)
ROBOBIKE_EMERGENCY_STOP_COMMAND: Final[str] = "stp_all"
# 停止系コマンド名リスト(sub_commandで未送信の他コマンドを破棄して優先送信する)
ROBOBIKE_STOP_COMMAND_NAMES: Final[list[str]] = [
    "stp_all",
    "bt_S",
    "bt_D_St",
]


# ROBOBIKE ステータス CSV インデックスリスト(すべて)
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
# ROBOBIKE ステータス CSV インデックスリスト長
ROBOBIKE_STATUS_CSV_INDEXES_LEN: Final[int] = len(ROBOBIKE_STATUS_CSV_INDEXES)

# ROBOBIKE ステータス CSV インデックスリスト(float値をとるもの)
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