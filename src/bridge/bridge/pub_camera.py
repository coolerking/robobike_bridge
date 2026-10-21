#!/usr/bin/env python3
"""
ファイル名: pub_camera.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にUSB接続され 
/dev/video<DEV_LETTER> として認識されているWebカメラデバイスを使って
PUBLISH_INTERVAL_SEC 間隔で撮影した静止画を
TOPICNAME_IMAGE トピックに配信します。

実行例:
    ros2 run monitor pub_camera
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


DEV_LETTER = 0  # /dev/video0
PUBLISH_INTERVAL_SEC = 0.05
TOPICNAME_IMAGE = 'camera_image'
ENCODING_TYPE = 'bgr8'

class ImagePublisherNode(Node):
    """
    ImagePublisherNode クラス

    Robobikeが使用するコース全体俯瞰できる画角のWebカメラ映像静止画を配信します。
    """

    def __init__(self):
        """
        ImagePublisherNode クラスの初期化処理

        ROS2 Publisher, CvBridge, and OpenCV VideoCapture の初期化を行います。
        """
        super().__init__('image_publisher')
        self.publisher = self.create_publisher(
            Image,
            TOPICNAME_IMAGE,
            10 # queue size
        )
        self.bridge = CvBridge()
        self.cap = cv2.VideoCapture(DEV_LETTER)
        ret, frame = self.cap.read()
        if ret:
            self.image_msg = self.bridge.cv2_to_imgmsg(frame, encoding=ENCODING_TYPE)
        else:
            self.get_logger().error('Failed to take a picture with cv2')
            raise OSError('Cannot take a picture with cv2')

        self.get_logger().info('ImagePublisherNode initialized successfully.')

    def take_picture(self):
        """
        静止画撮影を行い、撮影した画像を配信します。
        """
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding=ENCODING_TYPE)
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
    print('[main] start publisher')
    rclpy.init()
    image_publisher = ImagePublisherNode()
    try:
        import time
        while True:
            image_publisher.take_picture()
            print('[main] took picture')
            time.sleep(PUBLISH_INTERVAL_SEC)
    except KeyboardInterrupt:
        print('[main] publisher interrupted by user')
    finally:
        image_publisher.destroy_node()
        rclpy.shutdown()
        print('[main] publisher shutdown')


if __name__ == '__main__':
    main()
