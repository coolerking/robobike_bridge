#!/usr/bin/env python3
"""
ファイル名: sub_command.py


TOPICNAME_ROBOBIKE_COMMAND トピックを受信したら、
その内容をROBOBIKE操作系コマンドにして、
Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にWiFi接続されたROBOBIKEに対して操作系のコマンドを送信する。

実行例:
    ros2 run bridge sub_command --dummy --ros-args -r __node:=bike_test # ダミーデータでの実行
    ros2 run bridge sub_command --ros-args -r __node:=bike_test # 実機データでの実行
"""
import sys
import json
import argparse
import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from rclpy.utilities import remove_ros_args
from .robobike_bridge import RobobikeBridge

from .constants import QOS_PROFILE
from .constants import ROBOBIKE_DUMMY_IP
from .constants import TOPICNAME_ROBOBIKE_COMMAND
from .pub_command import CommandPublisher
from .robobike_utils import get_command_name

class RobobikeCommandSubscriber(Node):
    """
    ROBOBIKEへ操作系コマンドを送信するROS2ノードクラス。

    TOPICNAME_ROBOBIKE_COMMAND トピックを購読し、
    受信した内容をROBOBIKE操作系コマンドに変換して送信する。
    """
    def __init__(self, test:bool=False):
        """
        RobobikeCommandSubscriber クラスの初期化処理
        
        ROS2 Subscriber の初期化を行います。

        Args:
            test (bool): ダミーデータを使用するかどうか
        """
        super().__init__('robobike_command_subscriber_node')
        self.subscription = self.create_subscription(
            String,
            TOPICNAME_ROBOBIKE_COMMAND,
            self.receive_command,
            QOS_PROFILE
        )

        if test:
            self.broker = RobobikeBridge(ROBOBIKE_DUMMY_IP)
        else:
            self.broker = RobobikeBridge()

        self.get_logger().info('RobobikeCommandSubscriber initialized successfully.')

    def receive_command(self, msg: String) -> dict:
        """
        受信した操作系コマンドを処理し、ROBOBIKEに送信します。
        
        Args:
            msg (std_msgs.msg.String): 受信した操作系コマンドのメッセージ

        Returns:
            dict: ROBOBIKEへの送信結果を含む辞書
        
        Error:
            dict: command送信時の返却辞書(statusに'success'が含まれる)、もしくはエラー発生時の辞書(statusに'error'が含まれる)
        """
        try:
            self.get_logger().info(f'Received command: {msg.data}')
            command_dict = json.loads(msg.data)
            if not isinstance(command_dict, dict):
                raise ValueError('Command payload must be a JSON object')

            command_index = command_dict.get('command_index')
            if isinstance(command_index, bool) or not isinstance(command_index, int):
                raise ValueError('command_index must be an integer')
            command = get_command_name(command_index)

            raw_value = command_dict.get('value')
            if isinstance(raw_value, bool):
                raise ValueError('Command value must be numeric')
            value = None if raw_value is None else float(raw_value)
            if value is not None and not math.isfinite(value):
                raise ValueError(f'Command value must be finite: {raw_value}')
            if CommandPublisher.need_value(command_index) and value is None:
                raise ValueError(f'Command {command} requires a value')

            result = self.broker.send_command(command, value)
            if result.get('status') == 'error':
                self.get_logger().error(
                    f'Failed to send command {command}: {result.get("error", "Unknown error")}'
                )
                return {'status': 'error', 'error': f'Failed to send command {command}'}
            self.get_logger().info(
                f'Sent command: {command}, value: {value}, '
                f'status: {result.get("status")}'
            )
            result['status'] = 'success'
            return result
        except Exception as e:
            self.get_logger().error(f'Error processing command: {e}')
            return {'status': 'error', 'error': str(e)}

def main():
    """
    メイン関数

    TOPICNAME_ROBOBIKE_COMMAND トピックを購読して、ROBOBIKE操作系コマンドを処理するノードを起動します。
    Ctrl+C を押すと終了します。
    """
    parser = argparse.ArgumentParser(
        prog="sub_command",
        description="Subscribe ROBOBIKE commands and send them to the bike"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy data instead of the real ROBOBIKE')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)

    print(f'[main] start subscriber test:{str(args.dummy)}')
    rclpy.init()
    node = RobobikeCommandSubscriber(test=args.dummy)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('[main] Interrupt received')
    finally:
        node.destroy_node()
        rclpy.shutdown()
        print('[main] subscriber shutdown')

if __name__ == '__main__':
    main()
