"""ゲームパッドのデバイス設定と入力マッピング。"""
GAMEPAD_DEV_LETTER: int = 0
GAMEPAD_CHECK_INTERVAL_SEC: float = 0.1
GAMEPAD_ANALOG_CHANGE_THRESHOLD: float = 0.05
GAMEPAD_VALUE_THRESHOLD: float = 0.3

# ボタンに割り当てる特殊操作(ROBOBIKEコマンド番号は1以上なので0以下を使う)
GAMEPAD_ACTION_PUBLISH_START: int = 0    # Publish開始
GAMEPAD_ACTION_PUBLISH_STOP: int = -1    # Publish停止(緊急停止コマンド送信)
GAMEPAD_ACTION_EPISODE_START: int = -2   # Publish開始＋エピソード開始
GAMEPAD_ACTION_EPISODE_END: int = -3     # Publish停止(緊急停止コマンド送信)＋エピソード終了

GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING: list[str | int] = [
    "bt_S",    # 0:A
    "stp_all", # 1:B
    "bt_F",    # 2:X
    "bt_BK",   # 3:Y
    GAMEPAD_ACTION_PUBLISH_STOP,   # 4: LB    Publish Stop
    GAMEPAD_ACTION_PUBLISH_START,  # 5: RB    Publish Start
    GAMEPAD_ACTION_EPISODE_END,    # 6: BACK  Publish Stop + Episode End
    GAMEPAD_ACTION_EPISODE_START,  # 7: START Publish Start + Episode Start
    "stp_all", # 8: GUIDE(13)
    "bt_D_St", # 9: Left Stick(9)
    "bt_D_St", # 10: Right Stick(10)
]
GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING_LEN: int = len(
    GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING
)

GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING: list[list[str | None]] = [
    ["bt_Str_S", "bt_Str_S", "bt_Str_S"],  # 0: Left Stick X
    ["bt_A_Up", None, "bt_A_Dn"],            # 1: Left Stick Y
    [None, None, "stp_all"],                  # 2: LT(7)
    ["bt_Str_S", "bt_Str_S", "bt_Str_S"],  # 3: Right Stick X
    ["bt_A_Up", None, "bt_A_Dn"],            # 4: Right Stick Y
    [None, None, "stp_all"],                  # 5: RT(8)
]
GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING_LEN: int = len(
    GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING
)
