#!/usr/bin/env python3
"""
ファイル名: pub_robobike.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にWiFi接続された 
ROBOBIKEからPUBLISH_INTERVAL_SEC 間隔で取得したデータ("only_data")を
TOPICNAME_ROBOBIKE トピックに配信します。

実行例:
    ros2 run bridge pub_robobike --dummy --ros-args -r __node:=bike_test # ダミーデータでの実行
    ros2 run bridge pub_robobike --ros-args -r __node:=bike_test # 実機データでの実行
"""
import sys
import json
import argparse
from time import sleep
from .robobike_bridge import RobobikeBridge
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String
from rclpy.qos import QoSProfile


PUBLISH_INTERVAL_SEC = (float) (1/20.0)
TOPICNAME_ROBOBIKE_DATA = "robobike_data"
QUEUE_SIZE=10


class RobobikeDataPublisherNode(Node):
    """
    RobobikeDataPublisherNode クラス

    Robobikeからデータ取得し、トピックに配信します。
    """
    def __init__(self, test=False):
        """
        RobobikeDataPublisherNode クラスの初期化処理
        
        ROS2 Publisher, CvBridge, and OpenCV VideoCapture の初期化を行います。

        Args:
            test (bool): ダミーデータを使用するかどうか
        """
        super().__init__('robobike_data_publisher')
            
        self.publisher = self.create_publisher(
            String,
            TOPICNAME_ROBOBIKE_DATA,
            QoSProfile(depth=QUEUE_SIZE)
        )

        if test:
            self.broker = RobobikeBridge("127.0.0.1:8080")
        else:
            self.broker = RobobikeBridge()

        self.get_logger().info('RobobikeDataPublisherNode initialized successfully.')

    def send_robot_data(self) -> dict:
        """
        ROBOBIKEからデータを取得し、トピックに配信します。
        
        Returns:
            dict: 取得したROBOBIKEデータ
        """
        bike_data = self.broker.send_command()
        bike_data_str = json.dumps(bike_data)
        self.get_logger().info(f"Retrieved bike data: {bike_data_str}")
    
        msg = String()
        msg.data = bike_data_str
        self.publisher.publish(msg)
        self.get_logger().info("Published bike data")
        return bike_data

def main():
    """
    メイン関数

    PUBLISH_INTERVAL_SEC 間隔でROBOBIKEのデータを配信します。
    Ctrl+C を押すと終了します。
    """
    parser = argparse.ArgumentParser(
        prog="pub_robobike",
        description="Publish data from a WiFi-connected ROBOBIKE"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy data instead of real ROBOBIKE data')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)

    print(f'[main] start publisher test:{str(args.dummy)}')
    rclpy.init()
    node = RobobikeDataPublisherNode(test=args.dummy)
    try:
        while rclpy.ok():
            node.send_robot_data()
            sleep(PUBLISH_INTERVAL_SEC)
        print('[main] publisher stopped')
    except KeyboardInterrupt:
        print('[main] publisher interrupted by user')
    finally:
        node.destroy_node()
        rclpy.shutdown()
        print('[main] publisher shutdown')

if __name__ == "__main__":
    main()