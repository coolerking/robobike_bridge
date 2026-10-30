"""ROBOBIKEのコマンド・ステータス名変換ユーティリティ。"""
from .constants import ROBOBIKE_COMMAND_NAMES
from .constants import ROBOBIKE_STATUS_CSV_INDEXES
from .constants import ROBOBIKE_VALUE_MAX
from .constants import ROBOBIKE_VALUE_MIN


def get_command_index(button: str) -> int:
    """コマンド名を1始まりのコマンド番号に変換します。"""
    if button not in ROBOBIKE_COMMAND_NAMES:
        raise ValueError(f"Invalid button name: {button}")
    return ROBOBIKE_COMMAND_NAMES.index(button) + 1


def get_command_name(index: int) -> str:
    """1始まりのコマンド番号をコマンド名に変換します。"""
    if index < 1 or index > len(ROBOBIKE_COMMAND_NAMES):
        raise ValueError(f"Invalid command index: {index}")
    return ROBOBIKE_COMMAND_NAMES[index - 1]


def get_status_index(status: str) -> int:
    """ステータス名を0始まりのCSV項目番号に変換します。"""
    if status not in ROBOBIKE_STATUS_CSV_INDEXES:
        raise ValueError(f"Invalid status name: {status}")
    return ROBOBIKE_STATUS_CSV_INDEXES.index(status)


def get_status_name(index: int) -> str:
    """0始まりのCSV項目番号をステータス名に変換します。"""
    if index < 0 or index >= len(ROBOBIKE_STATUS_CSV_INDEXES):
        raise ValueError(f"Invalid status index: {index}")
    return ROBOBIKE_STATUS_CSV_INDEXES[index]


def normalize_value(value: float) -> int:
    """value値を整数に丸め、ROBOBIKE_VALUE_MIN〜ROBOBIKE_VALUE_MAXの範囲に収めます。"""
    return max(ROBOBIKE_VALUE_MIN, min(ROBOBIKE_VALUE_MAX, int(round(value))))
