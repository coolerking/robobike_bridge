#!/usr/bin/env python3
"""
ファイル名: sub_status.py

pub_status.py で配信されたステータス情報を購読して、表示します。
前提として pub_status.py が実行されていることが必要です。

Example:
    ros2 run bridge sub_status
"""

import json
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .constants import QOS_PROFILE
from .constants import TOPICNAME_ROBOBIKE_STATUS

# ステータス表示の最小間隔(秒)
LOG_THROTTLE_SEC = 1.0


class StatusSubscriber(Node):
    """
    StatusSubscriber クラス

    pub_status.py で配信されたステータス情報を購読して、表示します。
    """

    def __init__(self):
        """
        StatusSubscriber クラスの初期化処理

        ROS2 Subscriber の初期化を行います。
        """
        super().__init__('status_subscriber')
        self.subscriber = self.create_subscription(
            String,
            TOPICNAME_ROBOBIKE_STATUS,
            self.receive_status,
            QOS_PROFILE
        )
        self.get_logger().info('Status Subscriber node has been started.')

    def receive_status(self, msg: String) -> None:
        """
        pub_status.py で配信されたステータス情報を受信して、表示します。

        表示は LOG_THROTTLE_SEC 秒に1回に間引きます。

        Args:
            msg (String): pub_status.py で配信されたステータスメッセージ(JSON文字列)
        """
        try:
            status = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Invalid status JSON: {e}')
            return
        if not isinstance(status, dict):
            self.get_logger().error(f'Status must be a JSON object: {msg.data}')
            return

        self.get_logger().info(
            f"mot_spd={status.get('mot_spd')} str0={status.get('str0')} "
            f"gain_str={status.get('gain_str')} doSweep={status.get('doSweep')}",
            throttle_duration_sec=LOG_THROTTLE_SEC
        )


def main(args=None):
    """
    メイン関数

    pub_status.py で配信されたステータス情報を購読して、表示するノードを起動します。
    Ctrl+C を押すと終了します。
    """
    print('[main] start subscriber')
    rclpy.init(args=args)
    node: Optional[StatusSubscriber] = None
    try:
        node = StatusSubscriber()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('[main] Interrupt received')
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()
        print('[main] subscriber shutdown')


if __name__ == '__main__':
    main()
