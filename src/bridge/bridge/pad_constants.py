"""ゲームパッドのデバイス設定と入力マッピング。"""
GAMEPAD_DEV_LETTER: int = 0
GAMEPAD_CHECK_INTERVAL_SEC: float = 0.1
GAMEPAD_ANALOG_CHANGE_THRESHOLD: float = 0.05
GAMEPAD_VALUE_THRESHOLD: float = 0.3

GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING: list[str | int] = [
    "bt_S",    # 0:A
    "stp_all", # 1:B
    "bt_F",    # 2:X
    "bt_BK",   # 3:Y
    -1,         # 4: LB    Publish Stop
    0,          # 5: RB    Publish Start
    -1,         # 6: BACK  Publish Stop
    0,          # 7: START Publish Start
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
