"""Policy出力をROBOBIKEコマンドとしてpublishするノード。"""
import rclpy

from .pub_command import CommandPublisher


class PolicyCommandPublisher(CommandPublisher):
    """Policy実装を接続するための待機用Publisher。"""
    # TODO: 将来的に方策実行によるコマンドのpublishを実装する


def main() -> None:
    rclpy.init()
    node = PolicyCommandPublisher(node_name='policy_command_publisher')
    node.get_logger().info(
        "Policy publisher is idle; policy execution is not implemented yet."
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
