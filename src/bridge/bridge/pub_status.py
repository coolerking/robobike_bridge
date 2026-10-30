"""
ファイル名：pub_status.py

ROBOBIKEのステータス情報をPublishします。

実行例：
    ros2 run bridge pub_status # 実機の場合
    ros2 run bridge pub_status --dummy --ros-args --log-level debug # dummybikeの場合(実機不要)
"""
import sys
import time
import json
import typing
import argparse

# ROS2関連
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String

# 定数関連
from .constants import QOS_PROFILE
from .constants import ROBOBIKE_DUMMY_IP
from .constants import ROBOBIKE_DEFAULT_IP
from .constants import TOPICNAME_ROBOBIKE_STATUS
from .constants import PUBLISH_INTERVAL_SEC
from .constants import DEBUG


# ROBOBIKEブリッジ
from .robobike_bridge import RobobikeBridge


class StatusPublisher(Node):
    """
    StatusPublisherクラス

    ROBOBIKEのステータス情報を共通形式でpublishする。
    """

    def __init__(self, node_name: str = 'robobike_status_publisher') -> None:
        """
        初期化処理

        command only_data で取得できるステータス情報をpublishする準備を行います。

        Args:
            node_name (str): ROSノード名。デフォルトは 'robobike_status_publisher'。
        """
        super().__init__(node_name)
        self.publisher = self.create_publisher(
            String,
            TOPICNAME_ROBOBIKE_STATUS,
            QOS_PROFILE
        )

    def send_status(self, params: dict) -> None:
        """
        ステータス情報Publish送信処理

        ステータス辞書をJSON文字列として送信します。
        
        Args:
            params (dict): ステータス情報を含む辞書。
        """

        msg = String()
        msg.data = json.dumps(params)
        self.publisher.publish(msg)
        if DEBUG:
            self.get_logger().debug(f"Sent status: {msg.data}")


def main():
    """
    メイン関数

    PUBLISH_INTERVAL_SEC(--interval で変更可)間隔でROBOBIKEのonly_dataでえられるステータス情報を配信します。
    Ctrl+C を押すと終了します。
    """
    if DEBUG:
        print('[main] start publisher')

    # 引数処理
    parser = argparse.ArgumentParser(
        prog="pub_status",
        description="Publish ROBOBIKE status"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Connect to dummybike instead of the real ROBOBIKE')
    parser.add_argument(
        '--interval',
        type=float,
        default=PUBLISH_INTERVAL_SEC,
        help=f'Polling interval in seconds (default: {PUBLISH_INTERVAL_SEC})')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)
    if DEBUG:
        print(f'[main] start publisher test:{str(args.dummy)}')

    rclpy.init()
    status_publisher: typing.Optional[StatusPublisher] = None
    try:
        status_publisher = StatusPublisher()
        bridge = RobobikeBridge(default_ip=ROBOBIKE_DUMMY_IP if args.dummy else ROBOBIKE_DEFAULT_IP)
        while rclpy.ok():
            status = bridge.get_status()
            if status is not None and status.get('status') != 'error':
                status_publisher.send_status(status)
                if DEBUG:
                    print('[main] sent status')
            elif DEBUG:
                print(f'[main] error in status({status}), skipping')
            time.sleep(args.interval)
        if DEBUG:
            print('[main] publisher stopped')
    except KeyboardInterrupt:
        if DEBUG:
            print('[main] publisher interrupted by user')
    finally:
        try:
            if status_publisher is not None:
                status_publisher.destroy_node()
        finally:
            rclpy.try_shutdown()
        if DEBUG:
            print('[main] publisher shutdown')


if __name__ == '__main__':
    main()
