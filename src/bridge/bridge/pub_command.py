"""共通のROBOBIKEコマンドPublisherを定義します。"""
import json

from rclpy.duration import Duration
from rclpy.node import Node
from std_msgs.msg import String

from .constants import QOS_PROFILE
from .constants import ROBOBIKE_COMMAND_NAMES
from .constants import ROBOBIKE_COMMAND_NAMES_LEN
from .constants import ROBOBIKE_COMMAND_NAMES_REQUIRING_VALUE
from .constants import ROBOBIKE_EMERGENCY_STOP_COMMAND
from .constants import TOPICNAME_ROBOBIKE_COMMAND
from .robobike_utils import get_command_index

# ノード終了時の停止コマンドの配送完了を待つ最大時間(秒)
STOP_COMMAND_DELIVERY_TIMEOUT_SEC = 0.5


class CommandPublisher(Node):
    """ROBOBIKEコマンドを共通形式でpublishする基底クラス。"""

    def __init__(self, node_name: str = 'command_publisher'):
        super().__init__(node_name)
        self.is_publish = False
        self.publisher = self.create_publisher(
            String,
            TOPICNAME_ROBOBIKE_COMMAND,
            QOS_PROFILE
        )

    def send_command(self, params: dict) -> None:
        """Publishが有効な場合にコマンド辞書をJSON文字列として送信します。"""
        if not self.is_publish:
            self.get_logger().warning("Cannot send command: Publishing is stopped.")
            return

        msg = String()
        msg.data = json.dumps(params)
        self.publisher.publish(msg)
        self.get_logger().info(f"Sent command: {msg.data}")

    def send_stop_command(self) -> None:
        """
        緊急停止コマンドを送信します。

        Publish停止中でも送信します(停止方向の操作は常に許可する)。
        """
        msg = String()
        msg.data = json.dumps({
            "command_index": get_command_index(ROBOBIKE_EMERGENCY_STOP_COMMAND)
        })
        self.publisher.publish(msg)
        self.get_logger().warning(f"Sent stop command: {msg.data}")

    def start_pub(self) -> None:
        """コマンドのpublishを開始します。"""
        self.is_publish = True

    def stop_pub(self) -> None:
        """コマンドのpublishを停止します。"""
        self.is_publish = False

    def can_publish(self) -> bool:
        """現在コマンドをpublishできるかを返します。"""
        return self.is_publish

    @staticmethod
    def need_value(command_index: int | None) -> bool:
        """コマンド番号が値を必要とするかを返します。"""
        if command_index is None or not 1 <= command_index <= ROBOBIKE_COMMAND_NAMES_LEN:
            return False
        command_name = ROBOBIKE_COMMAND_NAMES[command_index - 1]
        return command_name in ROBOBIKE_COMMAND_NAMES_REQUIRING_VALUE

    def destroy_node(self) -> None:
        """
        publishを停止してからROSノードを破棄します。

        Publish中だった場合は緊急停止コマンドを送信し、配送完了を最大
        STOP_COMMAND_DELIVERY_TIMEOUT_SEC 秒待ちます。
        Ctrl+C 後に送信するには rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        で初期化し、rclpy のコンテキストが有効なうちに呼び出す必要があります。
        """
        if self.is_publish:
            try:
                self.send_stop_command()
                if not self.publisher.wait_for_all_acked(
                    Duration(seconds=STOP_COMMAND_DELIVERY_TIMEOUT_SEC)
                ):
                    self.get_logger().warning('Stop command delivery was not acknowledged.')
            except Exception as error:
                self.get_logger().error(f'Failed to send stop command on shutdown: {error}')
        self.stop_pub()
        super().destroy_node()
