#!/usr/bin/env python3
"""
ファイル名: pub_command.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTSにUSBドングル経由で接続された
ゲームパッドをテレオペ操作用デバイスにするためのモジュールです。
ゲームパッド操作をROBOBIKEのコマンド操作に変換して送信します。

実行例：
    ros2 run bridge pub_command_pad # 実機(ゲームパッドとUSBドングルをつないで)でのテスト実行
"""
import pygame
import sys
import rclpy

from .constants import DEBUG
from .pad_constants import GAMEPAD_ANALOG_CHANGE_THRESHOLD
from .pad_constants import GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING
from .pad_constants import GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING_LEN
from .pad_constants import GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING
from .pad_constants import GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING_LEN
from .pad_constants import GAMEPAD_CHECK_INTERVAL_SEC
from .pad_constants import GAMEPAD_DEV_LETTER
from .pad_constants import GAMEPAD_VALUE_THRESHOLD
from .pub_command import CommandPublisher
from .robobike_utils import get_command_index

class PadCommandPublisher(CommandPublisher):
    """
    ゲームパッド入力からROBOBIKEコマンドを生成するクラス。

    ゲームパッドの接続を確認し、親クラスの共通形式でコマンドを送信します。
    """
    def __init__(self, node_name: str = 'gamepad_publisher'):
        """
        ゲームパッドブリッジの初期化を行います。
        """
        # ノード名を 'gamepad_publisher' に設定して初期化
        super().__init__(node_name)

        # Publish可否フラグ
        self.stop_pub()

        # タイマーの設定
        self.timer = self.create_timer(
            GAMEPAD_CHECK_INTERVAL_SEC,
            self.timer_callback
            )

        # ゲームパッドの接続を確認
        pygame.init()

        # ゲームパッドの初期化
        pygame.joystick.init()

        # ゲームパッドが接続されているか確認
        if not 0 <= GAMEPAD_DEV_LETTER < pygame.joystick.get_count():
            self.get_logger().error(
                f"Gamepad device index {GAMEPAD_DEV_LETTER} is unavailable."
            )
            # ゲームパッドがないと意味がないので終了
            sys.exit(1)

        # 指定されたゲームパッドデバイス番号(/dev/input/jsX の X 部分)でジョイスティックを初期化
        self.joystick = pygame.joystick.Joystick(GAMEPAD_DEV_LETTER)

        # ジョイスティックを初期化
        self.joystick.init()
        self._axis_count = self.joystick.get_numaxes()
        self._button_count = self.joystick.get_numbuttons()
        self._invalid_gamepad_layout: tuple[int, int] | None = None
        if not self._validate_gamepad_layout():
            self.joystick.quit()
            sys.exit(1)
        self._gamepad_connected = True
        # ジョイスティック情報を格納する変数の初期化(初回は中立状態とする)
        self.joy_status = self.create_neutral_joy_status()

        # ゲームパッドの初期化完了メッセージをログに出力
        self.get_logger().info(f"Gamepad initialized: {self.joystick.get_name()}")

    def _validate_gamepad_layout(self) -> bool:
        if (
            self._axis_count < GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING_LEN
            or self._button_count < GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING_LEN
        ):
            layout = (self._axis_count, self._button_count)
            if layout != self._invalid_gamepad_layout:
                self.get_logger().error(
                    "Unsupported gamepad layout: "
                    f"{self._axis_count} axes and {self._button_count} buttons; "
                    f"requires at least "
                    f"{GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING_LEN} axes "
                    f"and {GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING_LEN} buttons."
                )
            self._invalid_gamepad_layout = layout
            return False

        self._invalid_gamepad_layout = None
        return True

    def _get_command_index_from_button_index(self, button_index: int) -> int:
        if button_index < 0 or button_index >= GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING_LEN:
            raise ValueError(f"Invalid button index: {button_index}")
        command = GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING[button_index]
        return command if isinstance(command, int) else get_command_index(command)

    def _get_command_params_from_axes(
        self,
        axes_index: int,
        axes_value: float
    ) -> dict | None:
        if not 0 <= axes_index < GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING_LEN:
            raise ValueError(f"Invalid axes index: {axes_index}")

        if axes_value <= GAMEPAD_VALUE_THRESHOLD - 1.0:
            order = 0
        elif axes_value >= 1.0 - GAMEPAD_VALUE_THRESHOLD:
            order = 2
        else:
            order = 1

        command_name = GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING[axes_index][order]
        if command_name is None:
            return None
        return {
            "command_index": get_command_index(command_name),
            "value": axes_value * 100.0,
        }

    def create_neutral_joy_status(self) -> dict:
        """
        ジョイスティックステータスを中立状態で作成します。

        Returns:
            dict: 作成した中立状態のメッセージを辞書形式で返します。
        """
        # 中立状態のジョイスティックメッセージを作成
        joy_status = {
            "header": {
                "stamp": self.get_clock().now().to_msg()
            },
            "axes": [0.0] * self._axis_count,    # 軸 (Axes): 0=左スティックX, 1=左スティックY, 2=右スティックX, 3=右スティックY ...
            "buttons": [0] * self._button_count  # ボタン (Buttons): 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=BACK, 7=START ...
        }
        return joy_status

    def _reset_joy_status(self) -> None:
        """比較用のゲームパッド状態を中立状態に戻します。"""
        self.joy_status = self.create_neutral_joy_status()

    def timer_callback(self) -> None:
        try:
            # ゲームパッドの状態を更新する
            pygame.event.pump()  # イベントキューを更新（必須）

            # ゲームパッドが接続されているか確認
            if not 0 <= GAMEPAD_DEV_LETTER < pygame.joystick.get_count():
                self.joystick = None
                if self._gamepad_connected:
                    self.get_logger().warning("Gamepad disconnected; waiting for reconnection.")
                    self._reset_joy_status()
                self._gamepad_connected = False
                return

            if self.joystick is None:
                self.joystick = pygame.joystick.Joystick(GAMEPAD_DEV_LETTER)
                self.joystick.init()
                self._axis_count = self.joystick.get_numaxes()
                self._button_count = self.joystick.get_numbuttons()
                if not self._validate_gamepad_layout():
                    self.joystick.quit()
                    self.joystick = None
                    self._gamepad_connected = False
                    return
                self._gamepad_connected = True
                self.get_logger().info(f"Gamepad reconnected: {self.joystick.get_name()}")

            axes = [
                self.joystick.get_axis(i)
                for i in range(self.joystick.get_numaxes())
            ]
            buttons = [
                self.joystick.get_button(i)
                for i in range(self.joystick.get_numbuttons())
            ]
        except pygame.error as error:
            self.joystick = None
            if self._gamepad_connected:
                self.get_logger().warning(f"Gamepad disconnected: {error}")
                self._reset_joy_status()
            self._gamepad_connected = False
            return
        except Exception as error:
            self.get_logger().error(f"Unexpected error: {error}")
            self._reset_joy_status()
            self._gamepad_connected = False
            self.joystick = None
            return

        # 現在のゲームパッドの状態を反映したジョイスティックステータスを作成
        ## 中立状態のジョイスティックメッセージを作成
        new_joy_status = self.create_neutral_joy_status()

        # ゲームパッドのアナログ入力情報を書き換え
        #   軸 (Axes): 0=左スティックX, 1=左スティックY, 2=右スティックX, 3=右スティックY ...
        new_joy_status["axes"] = axes
        
        # ゲームパッドのボタン入力情報を書き換え
        #   ボタン (Buttons): 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=BACK, 7=START ...
        new_joy_status["buttons"] = buttons

        # send_command対象リストを初期化
        command_value_list = []

        # self.joy_msgとnew_joy_msgを比較して、変化があった場合のみpublishを実行
        if self.joy_status is not None:
            # buttons の各値の変化があったかを判定し、変化あり兼押下のあったものを抽出する
            command_value_list = self._get_command_value_list_from_buttons(new_joy_status["buttons"])

            # axes の各値の変化がGAMEPAD_ANALOG_CHANGE_THRESHOLD以上の場合、変化があったと判断して抽出する
            axes_command_value_list = self._get_command_value_list_from_axes(new_joy_status["axes"])
            for axes_command_params in axes_command_value_list:
                command_value_list.append(axes_command_params)
            # send_command対象リストをログに出力
            if DEBUG:
                self.get_logger().debug(f"Target command value list: {command_value_list}")

        # command_value_listを順番にPublish
        for command_value in command_value_list:
            # Publish可能かを確認
            if self.can_publish():
                # コマンドをPublish送信
                self.send_command(command_value)
                if DEBUG:
                    self.get_logger().debug(f"Sent command: {command_value}")

        # 処理済みのジョイスティックステータスを履歴として保存
        self.joy_status = new_joy_status

    def _get_command_value_list_from_buttons(self, current_buttons: list[int]) -> list[dict]:
        """
        ボタン入力リストからコマンド値リストを作成する

        Args:
            current_buttons (list[int]): 現在のボタン入力値リスト

        Returns:
            list[dict]: コマンドと値(int)のペアが入った辞書のリスト(対象がない場合は空のリストを返す)
        """
        # command名とvalue値（Noneあり）の辞書を格納するリスト：send_command対象
        command_value_list:list[dict] = []
        # 現在のボタン入力値リストループ
        for current_button_index in range(GAMEPAD_BUTTON_INDEX_TO_COMMAND_MAPPING_LEN):
            # 対象インデックスのボタン値(現在)
            current_button_value = current_buttons[current_button_index]
            # 対象インデックスのボタン値(前回) 
            if self.joy_status is not None and self.joy_status["buttons"] is not None:
                previous_button_value = self.joy_status["buttons"][current_button_index]
                # ゲームパッドのボタンの値は押下時1、解除時0
                if current_button_value != previous_button_value and current_button_value == 1:
                    #コマンドインデックスに変換（ただし、0はPublish開始、-1はPublish停止を意味する）
                    current_command_index = self._get_command_index_from_button_index(
                        current_button_index
                    )
                    # command_index=0の場合Publish開始指示
                    if current_command_index == 0:
                        self.start_pub()
                    # command_index=-1の場合Publish停止指示
                    elif current_command_index == -1:
                        self.stop_pub()
                    # ROBOBIKE上のコマンドの場合、command_value_listに追加
                    else:
                        # 変化あり、かつ押下時はcommand_value_listに辞書を1件追加する
                        command_params = {
                            "command_index": current_command_index
                        }
                        # value値を持つコマンドかを判定する
                        if self.need_value(current_command_index):
                            # value値が必要→ボタン値範囲が(-1,1)を(-100,100)に変換
                            current_button_value = int(current_button_value * 100)
                            command_params["value"] = current_button_value
                        # デバッグログに追加した辞書を出力
                        if DEBUG:
                            self.get_logger().debug(f"Add command params: {command_params}")

                        # send_commandに渡すためにcommand_value_listに追加
                        command_value_list.append(command_params)

        # ループ終了後にcommand_value_listを返す
        if DEBUG:
            self.get_logger().debug(f"Return command value list(buttons): {command_value_list}")
        return command_value_list

    def _get_command_value_list_from_axes(self, current_axes: list[float]) -> list[dict]:
        """
        アナログ入力リストからコマンド値リストを作成する

        Args:
            current_axes (list[float]): 現在の軸入力値リスト

        Returns:
            list[dict]: コマンドと値(float)のペアが入った辞書のリスト(対象がない場合は空のリストを返す)
        """
        # command名とvalue値（Noneあり）の辞書を格納するリスト：send_command対象
        command_value_list = []
        # 現在のアナログ入力値リストループ
        for current_axis_index in range(GAMEPAD_AXES_INDEX_TO_COMMAND_MAPPING_LEN):
            # 対象インデックスのアナログ入力値(前回)
            previous_axis_value = self.joy_status["axes"][current_axis_index] if self.joy_status is not None else 0.0
            # 対象インデックスのアナログ入力値(現在)
            try:
                #float値として格納：(1.0, -1.0)の範囲
                current_axis_value = float(current_axes[current_axis_index])
            except (ValueError, TypeError):
                self.get_logger().warning(f"Invalid axis value at index {current_axis_index}: {current_axes[current_axis_index]}")
                # 変換不能の場合は、前回の値を代用
                current_axis_value = previous_axis_value

            # 前回と今回の値が閾値範囲外の変化があった場合に処理
            if abs(current_axis_value - previous_axis_value) >= GAMEPAD_ANALOG_CHANGE_THRESHOLD:
                # 値が変化したと判断した場合はsend_command対象として処理する
                command_params = self._get_command_params_from_axes(
                    current_axis_index,
                    current_axis_value
                )
                # send_command対象としてリストに追加
                if command_params is not None:
                    command_value_list.append(command_params)
                    if DEBUG:
                        self.get_logger().debug(f"add command params: {command_params}")

        # ループ終了後にcommand_value_listを返す
        if DEBUG:
            self.get_logger().debug(f"Return command value list(axes): {command_value_list}")
        return command_value_list

    def destroy_node(self) -> None:
        """
        ノードを破棄する際に呼ばれるメソッド。
        """
        self.stop_pub()
        super().destroy_node()

def main() -> None:
    rclpy.init()
    node = PadCommandPublisher()
    if DEBUG:
        print("Debug mode is ON.")
    print("GamepadPublisher node started.")
    print("Press Ctrl+C to exit.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Exiting...")
    finally:
        node.destroy_node()
        rclpy.shutdown()
        print("GamepadPublisher node stopped.")

if __name__ == '__main__':
    main()