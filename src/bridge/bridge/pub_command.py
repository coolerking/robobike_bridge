"""共通のROBOBIKEコマンドPublisherを定義します。"""
import json

from rclpy.node import Node
from std_msgs.msg import String

from .constants import QOS_PROFILE
from .constants import ROBOBIKE_COMMAND_NAMES
from .constants import ROBOBIKE_COMMAND_NAMES_LEN
from .constants import ROBOBIKE_COMMAND_NAMES_REQUIRING_VALUE
from .constants import TOPICNAME_ROBOBIKE_COMMAND


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
            self.get_logger().warn("Cannot send command: Publishing is stopped.")
            return

        msg = String()
        msg.data = json.dumps(params)
        self.publisher.publish(msg)
        self.get_logger().info(f"Sent command: {msg.data}")

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
        """publishを停止してからROSノードを破棄します。"""
        self.stop_pub()
        super().destroy_node()
