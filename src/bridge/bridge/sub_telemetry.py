#!/usr/bin/env python3
"""
ファイル名: sub_telemetry.py

pub_telemetry.py で配信されたテレメトリ情報を購読して、表示します。
前提として pub_telemetry.py が実行されていることが必要です。

Example:
    ros2 run bridge sub_telemetry
"""

import json
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .constants import QOS_PROFILE
from .constants import TOPICNAME_ROBOBIKE_TELEMETRY

# テレメトリ表示の最小間隔(秒)
LOG_THROTTLE_SEC = 1.0


class TelemetrySubscriber(Node):
    """
    TelemetrySubscriber クラス

    pub_telemetry.py で配信されたテレメトリ情報を購読して、表示します。
    """

    def __init__(self):
        """
        TelemetrySubscriber クラスの初期化処理

        ROS2 Subscriber の初期化を行います。
        """
        super().__init__('telemetry_subscriber')
        self.subscriber = self.create_subscription(
            String,
            TOPICNAME_ROBOBIKE_TELEMETRY,
            self.receive_telemetry,
            QOS_PROFILE
        )
        self.get_logger().info('Telemetry Subscriber node has been started.')

    def receive_telemetry(self, msg: String) -> None:
        """
        pub_telemetry.py で配信されたテレメトリ情報を受信して、表示します。

        表示は LOG_THROTTLE_SEC 秒に1回に間引きます。

        Args:
            msg (String): pub_telemetry.py で配信されたテレメトリメッセージ(JSON文字列)
        """
        try:
            telemetry = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Invalid telemetry JSON: {e}')
            return
        if not isinstance(telemetry, dict):
            self.get_logger().error(f'Telemetry must be a JSON object: {msg.data}')
            return

        def fmt(name: str) -> str:
            # float値はウィンドウ平均で誤差が出るため小数点以下3桁で表示
            value = telemetry.get(name)
            return f'{value:.3f}' if isinstance(value, float) else str(value)

        self.get_logger().info(
            f"time={fmt('time')} sv_pos={fmt('sv_pos')} "
            f"gy(roll,yaw,pitch)=({fmt('gy_roll')}, {fmt('gy_yaw')}, {fmt('gy_pitch')}) "
            f"acc(x,y,z)=({fmt('acc_x')}, {fmt('acc_y')}, {fmt('acc_z')})",
            throttle_duration_sec=LOG_THROTTLE_SEC
        )


def main(args=None):
    """
    メイン関数

    pub_telemetry.py で配信されたテレメトリ情報を購読して、表示するノードを起動します。
    Ctrl+C を押すと終了します。
    """
    print('[main] start subscriber')
    rclpy.init(args=args)
    node: Optional[TelemetrySubscriber] = None
    try:
        node = TelemetrySubscriber()
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
