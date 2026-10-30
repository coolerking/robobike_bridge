"""
ファイル名：pub_telemetry.py

ROBOBIKEのテレメトリ情報をPublishします。

実行例：
    ros2 run bridge pub_telemetry # 実機の場合
    ros2 run bridge pub_telemetry --dummy --ros-args --log-level debug # dummybikeの場合(実機不要)
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
from .constants import TOPICNAME_ROBOBIKE_TELEMETRY
from .constants import PUBLISH_INTERVAL_SEC
from .constants import DEBUG


# ROBOBIKEブリッジ
from .robobike_bridge import RobobikeBridge


class TelemetryPublisher(Node):
    """
    TelemetryPublisherクラス

    ROBOBIKEのテレメトリ情報を共通形式でpublishする。
    """

    def __init__(self, node_name: str = 'robobike_telemetry_publisher') -> None:
        """
        初期化処理

        get_acc で取得できるテレメトリ情報をpublishする準備を行います。

        Args:
            node_name (str): ROSノード名。デフォルトは 'robobike_telemetry_publisher'。
        """
        super().__init__(node_name)
        self.publisher = self.create_publisher(
            String,
            TOPICNAME_ROBOBIKE_TELEMETRY,
            QOS_PROFILE
        )

    def send_telemetry(self, params: dict) -> None:
        """
        テレメトリ情報Publish送信処理

        テレメトリ辞書をJSON文字列として送信します。
        
        Args:
            params (dict): テレメトリ情報を含む辞書。
        """

        msg = String()
        msg.data = json.dumps(params)
        self.publisher.publish(msg)
        if DEBUG:
            self.get_logger().debug(f"Sent telemetry: {msg.data}")


def main():
    """
    メイン関数

    PUBLISH_INTERVAL_SEC 間隔でROBOBIKEのget_accでえられるテレメトリ情報を配信します。
    Ctrl+C を押すと終了します。
    """
    if DEBUG:
        print('[main] start publisher')

    # 引数処理
    parser = argparse.ArgumentParser(
        prog="pub_telemetry",
        description="Publish ROBOBIKE telemetry"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Connect to dummybike instead of the real ROBOBIKE')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)
    if DEBUG:
        print(f'[main] start publisher test:{str(args.dummy)}')

    rclpy.init()
    telemetry_publisher: typing.Optional[TelemetryPublisher] = None
    try:
        telemetry_publisher = TelemetryPublisher()
        bridge = RobobikeBridge(default_ip=ROBOBIKE_DUMMY_IP if args.dummy else ROBOBIKE_DEFAULT_IP)
        while rclpy.ok():
            telemetry = bridge.get_telemetry()
            if telemetry is None:
                # 新規データなし(前回取得分のみ)の場合は送信しない
                pass
            elif telemetry.get('status') != 'error':
                telemetry_publisher.send_telemetry(telemetry)
                if DEBUG:
                    print('[main] sent telemetry')
            elif DEBUG:
                print(f'[main] error in telemetry({telemetry}), skipping')
            time.sleep(PUBLISH_INTERVAL_SEC)
        if DEBUG:
            print('[main] publisher stopped')
    except KeyboardInterrupt:
        if DEBUG:
            print('[main] publisher interrupted by user')
    finally:
        try:
            if telemetry_publisher is not None:
                telemetry_publisher.destroy_node()
        finally:
            rclpy.try_shutdown()
        if DEBUG:
            print('[main] publisher shutdown')


if __name__ == '__main__':
    main()
