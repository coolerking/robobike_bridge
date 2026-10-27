#!/usr/bin/env python3
"""
ファイル名: sub_robobike.py


TOPICNAME_ROBOBIKE_CONTROL トピックを受信したら、
その内容をROBOBIKE操作系コマンドにして、
Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にWiFi接続されたROBOBIKEに対して操作系のコマンドを送信する。

実行例:
    ros2 run bridge sub_robobike --dummy --ros-args -r __node:=bike_test # ダミーデータでの実行
    ros2 run bridge sub_robobike --ros-args -r __node:=bike_test # 実機データでの実行
"""
import sys
import json
import argparse
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String
from rclpy.utilities import remove_ros_args
from .robobike import RobobikeBridge

TOPICNAME_ROBOBIKE_CONTROL = "robobike_control"
QUEUE_SIZE=10

class RobobikeSubscriberNode(Node):
    """
    ROBOBIKEへ操作系コマンドを送信するROS2ノードクラス。

    TOPICNAME_ROBOBIKE_CONTROL トピックを購読し、
    受信した内容をROBOBIKE操作系コマンドに変換して送信する。
    """
    def __init__(self, test:bool=False):
        """
        RobobikeSubscriberNode クラスの初期化処理
        
        ROS2 Subscriber の初期化を行います。

        Args:
            test (bool): ダミーデータを使用するかどうか
        """
        super().__init__('robobike_subscriber_node')
        self.subscription = self.create_subscription(
            String,
            TOPICNAME_ROBOBIKE_CONTROL,
            self.recieve_control_command,
            QoSProfile(depth=QUEUE_SIZE)
        )

        if test:
            self.broker = RobobikeBridge("127.0.0.1:8080")
        else:
            self.broker = RobobikeBridge()

        self.get_logger().info('RobobikeSubscriberNode initialized successfully.')

    def recieve_control_command(self, msg) -> dict:
        """
        受信した制御コマンドを処理し、ROBOBIKEに送信します。
        
        Args:
            msg (std_msgs.msg.String): 受信した制御コマンドのメッセージ

        Returns:
            dict: ROBOBIKEへの送信結果を含む辞書
        
        Error:
            dict: command送信時の返却辞書(statusに'success'が含まれる)、もしくはエラー発生時の辞書(statusに'error'が含まれる)
        """
        try:
            self.get_logger().info(f'Received control command: {msg.data}')
            control_dict = json.loads(msg.data)
            command = control_dict.get('command', 'only_data')

            value_str = control_dict.get('value', None)
            if value_str is not None:
                try:
                    value = float(value_str)
                except ValueError:
                    self.get_logger().error(f'Invalid value: {value_str}')
                    return {'status': 'error', 'error': f'Invalid value: {value_str}'}
            else:
                value = None

            result = self.broker.send_command(command, value)
            if result.get('status') == 'error':
                self.get_logger().error(
                    f'Failed to send command {command}: {result.get("error", "Unknown error")}'
                )
                return {'status': 'error', 'error': f'Failed to send command {command}'}
            self.get_logger().info(f'Sent command: {command}, value: {value}, status: {result.get("status")}')
            result['status'] = 'success'
            return result
        except Exception as e:
            self.get_logger().error(f'Error processing control command: {e}')
            return {'status': 'error', 'error': str(e)}

def main(args=None):
    """
    メイン関数

    TOPICNAME_ROBOBIKE_CONTROL トピックを購読して、ROBOBIKE操作系コマンドを処理するノードを起動します。
    Ctrl+C を押すと終了します。
    """
    parser = argparse.ArgumentParser(
        prog="sub_robobike",
        description="Subscribe control command and value to a WiFi-connected ROBOBIKE"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy data instead of real ROBOBIKE')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)

    print(f'[main] start subscriber test:{str(args.dummy)}')
    rclpy.init()
    node = RobobikeSubscriberNode(test=args.dummy)
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
