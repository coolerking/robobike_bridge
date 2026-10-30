"""
Policy出力をROBOBIKEコマンドとしてpublishするノード。

制御周期(POLICY_CONTROL_INTERVAL_SEC)ごとに方策ハートビートを送信する。
sub_command を --watchdog 付きで起動すると、ハートビートが途絶えた場合に緊急停止する。

実行例:
    ros2 run bridge pub_command_policy
"""
import rclpy
from std_msgs.msg import Header

from .constants import HEARTBEAT_QOS_PROFILE
from .constants import POLICY_CONTROL_INTERVAL_SEC
from .constants import TOPICNAME_POLICY_HEARTBEAT
from .pub_command import CommandPublisher


class PolicyCommandPublisher(CommandPublisher):
    """Policy実装を接続するための待機用Publisher。"""

    def __init__(self, node_name: str = 'policy_command_publisher'):
        super().__init__(node_name)
        self.heartbeat_publisher = self.create_publisher(
            Header,
            TOPICNAME_POLICY_HEARTBEAT,
            HEARTBEAT_QOS_PROFILE
        )
        self.timer = self.create_timer(POLICY_CONTROL_INTERVAL_SEC, self.control_step)

    def control_step(self) -> None:
        """
        制御周期ごとの処理。

        ハートビートは推論が完了した後に送信する
        (推論が止まった場合にウォッチドッグが検知できるようにするため)。
        """
        # TODO: 将来的に方策実行によるコマンドのpublishを実装する
        self.send_heartbeat()

    def send_heartbeat(self) -> None:
        """方策ハートビートを送信します。"""
        msg = Header()
        msg.stamp = self.get_clock().now().to_msg()
        msg.frame_id = self.get_name()
        self.heartbeat_publisher.publish(msg)


def main() -> None:
    rclpy.init()
    node = PolicyCommandPublisher(node_name='policy_command_publisher')
    node.get_logger().info(
        "Policy publisher is sending heartbeats only; policy execution is not implemented yet."
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
