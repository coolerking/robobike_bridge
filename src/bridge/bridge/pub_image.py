#!/usr/bin/env python3
"""
ファイル名: pub_image.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にUSB接続され 
/dev/video<IMAGE_DEV_LETTER> として認識されているWebカメラデバイスを使って
PUBLISH_INTERVAL_SEC 間隔で撮影した静止画を
TOPICNAME_IMAGE トピックに配信します。

実行例:
    ros2 run monitor pub_image # 実カメラ使用
    ros2 run monitor pub_image --dummy # ダミー画像使用
"""
import sys
import numpy as np
import argparse
from typing import Optional
from rclpy.utilities import remove_ros_args
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge


# 定数のインポート
from .constants import DEBUG
from .constants import CAMERA_DEV_LETTER
from .constants import PUBLISH_INTERVAL_SEC
from .constants import TOPICNAME_IMAGE
from .constants import IMAGE_ENCODING_TYPE
from .constants import QOS_PROFILE

class ImagePublisher(Node):
    """
    ImagePublisher クラス

    Robobikeが使用するコース全体俯瞰できる画角のWebカメラ映像静止画を配信します。
    """

    def __init__(self, test: bool=False):
        """
        ImagePublisher クラスの初期化処理

        ROS2 Publisher, CvBridge, and OpenCV VideoCapture の初期化を行います。

        Args:
            test (bool): ダミー画像を使用するかどうかのフラグ。デフォルトは False。
        """
        super().__init__('image_publisher')
        self.test = test
        self.cap: Optional[cv2.VideoCapture] = None
        self.publisher = self.create_publisher(
            Image,
            TOPICNAME_IMAGE,
            QOS_PROFILE
        )

        self.bridge = CvBridge()
        if self.test:
            # ダミー画像を使用
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            self.image_msg = self.bridge.cv2_to_imgmsg(dummy_frame, encoding=IMAGE_ENCODING_TYPE)
        else:
            # 実際のカメラを使用
            self.cap = cv2.VideoCapture(CAMERA_DEV_LETTER)
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.get_logger().error('Failed to take a picture with cv2')
                    raise OSError('Cannot take a picture with cv2')
                self.image_msg = self.bridge.cv2_to_imgmsg(frame, encoding=IMAGE_ENCODING_TYPE)
            except Exception:
                self.destroy_node()
                raise

        self.get_logger().info(f'ImagePublisher(test={self.test}) initialized successfully.')

    def destroy_node(self) -> None:
        """
        ROSノードを破棄する前に呼ばれる処理

        ROSノードを破棄する前に、カメラを解放する
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        super().destroy_node()

    def take_picture(self):
        """
        静止画撮影を行い、撮影した画像を配信します。
        """
        if self.test:
            self.publisher.publish(self.image_msg)
            self.get_logger().info('Published dummy picture successfully.')
        else:
            assert self.cap is not None
            ret, frame = self.cap.read()
            if ret:
                msg = self.bridge.cv2_to_imgmsg(frame, encoding=IMAGE_ENCODING_TYPE)
                self.publisher.publish(msg)
                self.image_msg = msg
                self.get_logger().info('Picture taken and published successfully.')
            else:
                self.get_logger().error('Failed to take a picture with cv2')


def main():
    """
    メイン関数

    PUBLISH_INTERVAL_SEC 間隔でWebカメラの静止画を配信します。
    Ctrl+C を押すと終了します。
    """
    if DEBUG:
        print('[main] start publisher')

    # 引数処理
    parser = argparse.ArgumentParser(
        prog="pub_camera",
        description="Publish camera image"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy camera image instead of real ROBOBIKE data')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)
    if DEBUG:
        print(f'[main] start publisher test:{str(args.dummy)}')

    rclpy.init()
    image_publisher: Optional[ImagePublisher] = None
    try:
        image_publisher = ImagePublisher(test=args.dummy)
        import time
        while rclpy.ok():
            image_publisher.take_picture()
            if DEBUG:
                print('[main] took picture')
            time.sleep(PUBLISH_INTERVAL_SEC)
        if DEBUG:
            print('[main] publisher stopped')
    except KeyboardInterrupt:
        if DEBUG:
            print('[main] publisher interrupted by user')
    finally:
        try:
            if image_publisher is not None:
                image_publisher.destroy_node()
        finally:
            rclpy.shutdown()
        if DEBUG:
            print('[main] publisher shutdown')


if __name__ == '__main__':
    main()
