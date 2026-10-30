#!/usr/bin/env python3
"""
ファイル名: sub_image.py

pub_image.py で配信されたカメラ画像(JPEG圧縮)を購読して、CV2 で表示します。
前提として pub_image.py が実行されていること、そしてGUI環境が利用可能であることが必要です。

Example:
    ros2 run bridge sub_image
"""

import rclpy
from typing import Optional
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import numpy as np
import cv2

from .constants import TOPICNAME_IMAGE
from .constants import IMAGE_QOS_PROFILE

class ImageSubscriber(Node):
    """
    ImageSubscriber クラス

    pub_image.py で配信されたカメラ画像を購読して、CV2 で表示します。
    """

    def __init__(self):
        """
        ImageSubscriber クラスの初期化処理

        ROS2 Subscriber の初期化を行います。
        """
        super().__init__('image_subscriber')
        self.subscriber = self.create_subscription(
            CompressedImage,
            TOPICNAME_IMAGE,
            self.recieve_camera_image,
            IMAGE_QOS_PROFILE
        )
        self.subscriber
        self.get_logger().info('Image Subscriber node has been started.')

    def recieve_camera_image(self, msg: CompressedImage):
        """
        pub_image.py で配信されたカメラ画像を受信・展開して、CV2 で表示します。
        GUI環境での表示を前提としています。

        Args:
            msg (CompressedImage): pub_image.py で配信されたカメラ画像メッセージ
        """
        try:
            self.get_logger().debug('Received camera image:')
            frame = cv2.imdecode(np.frombuffer(msg.data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError(f'Failed to decode {msg.format} image')
            cv2.imshow('Camera View', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')

def main(args=None):
    """
    メイン関数

    pub_image.py で配信されたカメラ画像を購読して、CV2 で表示するノードを起動します。
    Ctrl+C を押すと終了します。
    """
    print('[main] start subscriber')
    rclpy.init(args=args)
    node: Optional[ImageSubscriber] = None
    try:
        node = ImageSubscriber()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('[main] Interrupt received')
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            try:
                rclpy.try_shutdown()
            finally:
                cv2.destroyAllWindows()
        print('[main] subscriber shutdown')

if __name__ == '__main__':
    main()
