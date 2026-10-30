"""
ファイル名：calibration.py

Robobike のモータ速度(mot_spd)を目標値に調整する

実行例：
    ros2 run bridge calibration                  # 実機、目標値はデフォルト
    ros2 run bridge calibration --mot_spd 15     # 実機、目標値を指定
    ros2 run bridge calibration --dummy          # dummybike でのテスト実行
"""
import argparse
import time
from typing import Final, Optional

from .robobike_bridge import RobobikeBridge
# ROBOBIKE 実機 IPアドレス
from .constants import ROBOBIKE_DEFAULT_IP
# dummyserver IPアドレス
from .constants import ROBOBIKE_DUMMY_IP
# 緊急停止コマンド名
from .constants import ROBOBIKE_EMERGENCY_STOP_COMMAND

# mot_spd の目標値(デフォルト)
DEFAULT_TARGET_MOT_SPD: Final[int] = 10
# 調整コマンドの最大送信回数(無限ループ防止)
MAX_ITERATIONS: Final[int] = 100
# 調整コマンド送信間隔(秒)
COMMAND_INTERVAL_SEC: Final[float] = 1.0


def _get_mot_spd(status: Optional[dict]) -> int:
    """
    ステータス辞書から mot_spd を取り出します。

    Args:
        status (Optional[dict]): send_command()/get_status() の戻り値

    Returns:
        int: mot_spd の値

    Raises:
        RuntimeError: 通信エラー、または mot_spd が取得できない場合
    """
    if status is None:
        raise RuntimeError('Failed to get status from Robobike: no response')
    if status.get('status') == 'error':
        raise RuntimeError(f"Failed to get status from Robobike: {status.get('error')}")
    mot_spd = status.get('mot_spd')
    if not isinstance(mot_spd, int):
        raise RuntimeError(f'Invalid mot_spd in status: {mot_spd!r}')
    return mot_spd


def main() -> None:
    # 引数処理
    parser = argparse.ArgumentParser(
        prog="calibration",
        description="Calibrate ROBOBIKE mot_spd"
    )
    # ターゲット値(int)を指定する引数
    parser.add_argument(
        '--mot_spd',
        type=int,
        default=DEFAULT_TARGET_MOT_SPD,
        help=f'Target mot_spd value (default: {DEFAULT_TARGET_MOT_SPD})')
    # ダミーを使うかどうかを指定する引数
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy ROBOBIKE instead of real ROBOBIKE')
    args = parser.parse_args()
    target_mot_spd = args.mot_spd
    default_ip = ROBOBIKE_DUMMY_IP if args.dummy else ROBOBIKE_DEFAULT_IP

    print("Starting calibration...")
    print(f"Using robobike IP: {default_ip}")
    print(f"Target mot_spd: {target_mot_spd}")

    # RobobikeBridgeインスタンスを作成
    bridge = RobobikeBridge(default_ip=default_ip)
    try:
        # ROBOBIKEのステータスを取得
        mot_spd = _get_mot_spd(bridge.get_status())

        for _ in range(MAX_ITERATIONS):
            # mot_spd が目標値
            if mot_spd == target_mot_spd:
                print(f"mot_spd {mot_spd} is equal to target {target_mot_spd}")
                break
            elif mot_spd < target_mot_spd:
                print(f"mot_spd {mot_spd} is below target {target_mot_spd}")
                button = "bt_A_Up_0"
            else:
                print(f"mot_spd {mot_spd} is above target {target_mot_spd}")
                button = "bt_A_Dn_0"
            # 戻り値に更新後のステータスが入っているのでそのまま使う
            mot_spd = _get_mot_spd(bridge.send_command(button=button))
            time.sleep(COMMAND_INTERVAL_SEC)
        else:
            raise RuntimeError(
                f'mot_spd did not reach target {target_mot_spd} '
                f'within {MAX_ITERATIONS} iterations (current: {mot_spd})'
            )

        print(f"Calibration completed. Final mot_spd: {mot_spd}")
    finally:
        # 正常終了・例外・Ctrl+C いずれの場合も全ての動作を停止
        print(f"Sending {ROBOBIKE_EMERGENCY_STOP_COMMAND} command...")
        result = bridge.send_command(button=ROBOBIKE_EMERGENCY_STOP_COMMAND)
        if result.get('status') == 'error':
            print(f"WARNING: failed to send {ROBOBIKE_EMERGENCY_STOP_COMMAND}: {result.get('error')}")


if __name__ == "__main__":
    main()
