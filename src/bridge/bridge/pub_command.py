#!/usr/bin/env python3
"""
ファイル名: pub_command.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTSにUSBドングル経由で接続された
ゲームパッドをテレオペ操作用デバイスにするためのモジュールです。
ゲームパッド操作をROBOBIKEのコマンド操作に変換して送信します。

実行例：
    ros2 run bridge pub_command # 実機(ゲームパッドとUSBドングルをつないで)でのテスト実行
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import pygame
import sys

# QoS設定
from .constants import QOS_PROFILE

# トピック名設定（ジョイスティックデータ）
from .constants import TOPICNAME_JOY

# QoS設定
from .constants import QOS_PROFILE

# ゲームパッドデバイス番号設定
from .constants import GAMEPAD_DEV_LETTER

# ゲームパッド入力チェックの間隔
from .constants import GAMEPAD_CHECK_INTERVAL_SEC

# ゲームパッドアナログ値変化有無を判断する閾値
from .constants import GAMEPAD_ANALOG_CHANGE_THRESHOLD

# デバッグフラグ
from .constants import DEBUG

class GamepadPublisher(Node):
    """
    ゲームパッドをROS2のJoyトピックにブリッジするクラス。

    ゲームパッドの接続を確認し、ROS2のJoyトピックにゲームパッドの入力を送信します。
    """
    def __init__(self):
        """
        ゲームパッドブリッジの初期化を行います。
        """
        # ノード名を 'gamepad_publisher' に設定して初期化
        super().__init__('gamepad_publisher')

        # ゲームパッド入力を送信するためのJoyトピックパブリッシャを作成
        self.joy_pub = self.create_publisher(
            Joy,
            TOPICNAME_JOY,
            QOS_PROFILE
            )

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
        self._gamepad_connected = True
        # ジョイスティック情報を格納する変数の初期化
        self.joy_msg = self._publish_neutral_joy(do_publish=False)

        # ゲームパッドの初期化完了メッセージをログに出力
        self.get_logger().info(f"Gamepad initialized: {self.joystick.get_name()}")

    def _publish_neutral_joy(self, do_publish:bool=True) -> Joy:
        """
        Joyメッセージを中立状態で作成し、パブリッシュします。

        Args:
            do_publish (bool): Trueの場合、作成したJoyメッセージをパブリッシュします。
        Returns:
            Joy: 作成した中立状態のJoyメッセージ。
        """
        # 中立状態のJoyメッセージを作成
        neutral_msg = Joy()
        neutral_msg.header.stamp = self.get_clock().now().to_msg()
        neutral_msg.axes = [0.0] * self._axis_count
        neutral_msg.buttons = [0] * self._button_count
        if do_publish:
            self.joy_pub.publish(neutral_msg)
        return neutral_msg

    def timer_callback(self) -> None:
        try:
            # ゲームパッドの状態を更新する
            pygame.event.pump()  # イベントキューを更新（必須）

            # ゲームパッドが接続されているか確認
            if not 0 <= GAMEPAD_DEV_LETTER < pygame.joystick.get_count():
                self.joystick = None
                if self._gamepad_connected:
                    self.get_logger().warning("Gamepad disconnected; waiting for reconnection.")
                    self._publish_neutral_joy()
                self._gamepad_connected = False
                return

            if self.joystick is None:
                self.joystick = pygame.joystick.Joystick(GAMEPAD_DEV_LETTER)
                self.joystick.init()
                self._axis_count = self.joystick.get_numaxes()
                self._button_count = self.joystick.get_numbuttons()
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
                self._publish_neutral_joy()
            self._gamepad_connected = False
            return

        # Joyメッセージを作成
        new_joy_msg = Joy()
        
        # ヘッダのタイムスタンプを現在時刻で設定
        new_joy_msg.header.stamp = self.get_clock().now().to_msg()

        # ゲームパッドのアナログ入力情報を取得
        #   軸 (Axes): 0=左スティックX, 1=左スティックY, 2=右スティックX, 3=右スティックY ...
        new_joy_msg.axes = axes
        
        # ゲームパッドのボタン入力情報を取得
        #   ボタン (Buttons): 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=BACK, 7=START ...
        new_joy_msg.buttons = buttons

        # self.joy_msgとnew_joy_msgを比較して、変化があった場合のみpublishを実行
        if self.joy_msg is not None:
            # axes の各値の変化がGAMEPAD_ANALOG_CHANGE_THRESHOLD以上の場合、変化があったと判断する
            if any(abs(a - b) >= GAMEPAD_ANALOG_CHANGE_THRESHOLD for a, b in zip(self.joy_msg.axes, new_joy_msg.axes)):
                pass
            elif self.joy_msg.buttons == new_joy_msg.buttons:
                if DEBUG:
                    self.get_logger().debug("No significant change in Joy message; not publishing.")
                return

        # JoyメッセージをPublish
        self.joy_pub.publish(new_joy_msg)
        # Publish後にself.joy_msgを更新
        self.joy_msg = new_joy_msg

        if DEBUG:
            self.get_logger().debug(f"Published Joy message. {new_joy_msg}")
            print(f"Published Joy message. {new_joy_msg}")


def main() -> None:
    rclpy.init()
    node = GamepadPublisher()
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