#!/usr/bin/env python3
"""
ファイル名: pub_image.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にUSB接続され
/dev/video<CAMERA_DEV_LETTER> として認識されているWebカメラデバイスを使って
IMAGE_PUBLISH_INTERVAL_SEC(--interval で変更可)間隔で撮影した静止画を
IMAGE_WIDTH x IMAGE_HEIGHT に縮小・JPEG圧縮して
TOPICNAME_IMAGE トピックに sensor_msgs/CompressedImage として配信します。

実行例:
    ros2 run bridge pub_image # 実カメラ使用
    ros2 run bridge pub_image --dummy # ダミー画像使用
    ros2 run bridge pub_image --interval 0.05 # 20Hzで配信
"""
import sys
import time
import numpy as np
import argparse
from typing import Optional
from rclpy.utilities import remove_ros_args
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import cv2


# 定数のインポート
from .constants import DEBUG
from .constants import CAMERA_DEV_LETTER
from .constants import IMAGE_PUBLISH_INTERVAL_SEC
from .constants import TOPICNAME_IMAGE
from .constants import IMAGE_QOS_PROFILE
from .constants import IMAGE_WIDTH
from .constants import IMAGE_HEIGHT
from .constants import IMAGE_COMPRESSED_FORMAT
from .constants import IMAGE_JPEG_QUALITY
from .constants import IMAGE_FRAME_ID

class ImagePublisher(Node):
    """
    ImagePublisher クラス

    Robobikeが使用するコース全体俯瞰できる画角のWebカメラ映像静止画を配信します。
    """

    def __init__(self, test: bool=False):
        """
        ImagePublisher クラスの初期化処理

        ROS2 Publisher, and OpenCV VideoCapture の初期化を行います。

        Args:
            test (bool): ダミー画像を使用するかどうかのフラグ。デフォルトは False。
        """
        super().__init__('image_publisher')
        self.test = test
        self.cap: Optional[cv2.VideoCapture] = None
        # ダミー画像に描画するフレーム番号
        self.frame_count = 0
        self.publisher = self.create_publisher(
            CompressedImage,
            TOPICNAME_IMAGE,
            IMAGE_QOS_PROFILE
        )

        if not self.test:
            # 実際のカメラを使用
            self.cap = cv2.VideoCapture(CAMERA_DEV_LETTER)
            try:
                # カメラ側の解像度は変更しない(非対応の解像度を指定すると GStreamer の
                # パイプラインが起動できなくなるため)。縮小は送信前に行う。
                ret, _ = self.cap.read()
                if not ret:
                    self.get_logger().error('Failed to take a picture with cv2')
                    raise OSError('Cannot take a picture with cv2')
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

    def create_dummy_frame(self) -> np.ndarray:
        """
        ダミー画像を作成します。

        実画像に近い圧縮サイズになるようグラデーションを描き、
        受信側で更新を確認できるようフレーム番号を描画します。

        Returns:
            np.ndarray: IMAGE_HEIGHT x IMAGE_WIDTH の BGR 画像
        """
        x = np.linspace(0, 255, IMAGE_WIDTH, dtype=np.uint8)
        y = np.linspace(0, 255, IMAGE_HEIGHT, dtype=np.uint8)
        frame = np.dstack([
            np.tile(x, (IMAGE_HEIGHT, 1)),
            np.tile(y[:, None], (1, IMAGE_WIDTH)),
            np.full((IMAGE_HEIGHT, IMAGE_WIDTH), (self.frame_count * 5) % 256, dtype=np.uint8),
        ])
        cv2.putText(
            frame, f'DUMMY #{self.frame_count}', (10, IMAGE_HEIGHT // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2
        )
        self.frame_count += 1
        return frame

    def create_compressed_msg(self, frame: np.ndarray) -> Optional[CompressedImage]:
        """
        画像を IMAGE_WIDTH x IMAGE_HEIGHT に縮小・JPEG圧縮してメッセージを作成します。

        Args:
            frame (np.ndarray): BGR 画像

        Returns:
            Optional[CompressedImage]: 作成したメッセージ、圧縮に失敗した場合は None
        """
        if frame.shape[1] != IMAGE_WIDTH or frame.shape[0] != IMAGE_HEIGHT:
            frame = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, IMAGE_JPEG_QUALITY])
        if not ok:
            self.get_logger().error('Failed to encode a picture to JPEG')
            return None
        msg = CompressedImage()
        # 撮影時刻(受信側で status/telemetry と時刻を合わせるために使う)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = IMAGE_FRAME_ID
        msg.format = IMAGE_COMPRESSED_FORMAT
        msg.data = encoded.tobytes()
        return msg

    def take_picture(self):
        """
        静止画撮影を行い、撮影した画像を配信します。
        """
        if self.test:
            frame = self.create_dummy_frame()
        else:
            assert self.cap is not None
            ret, frame = self.cap.read()
            if not ret:
                self.get_logger().error('Failed to take a picture with cv2')
                return
        msg = self.create_compressed_msg(frame)
        if msg is None:
            return
        self.publisher.publish(msg)
        if DEBUG:
            self.get_logger().debug(f'Picture published successfully ({len(msg.data)} bytes).')


def main():
    """
    メイン関数

    IMAGE_PUBLISH_INTERVAL_SEC(--interval で変更可)間隔でWebカメラの静止画を配信します。
    Ctrl+C を押すと終了します。
    """
    if DEBUG:
        print('[main] start publisher')

    # 引数処理
    parser = argparse.ArgumentParser(
        prog="pub_image",
        description="Publish camera image"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy camera image instead of real ROBOBIKE data')
    parser.add_argument(
        '--interval',
        type=float,
        default=IMAGE_PUBLISH_INTERVAL_SEC,
        help=f'Publish interval in seconds (default: {IMAGE_PUBLISH_INTERVAL_SEC})')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)
    if DEBUG:
        print(f'[main] start publisher test:{str(args.dummy)}')

    rclpy.init()
    image_publisher: Optional[ImagePublisher] = None
    try:
        image_publisher = ImagePublisher(test=args.dummy)
        while rclpy.ok():
            image_publisher.take_picture()
            if DEBUG:
                print('[main] took picture')
            time.sleep(args.interval)
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
            rclpy.try_shutdown()
        if DEBUG:
            print('[main] publisher shutdown')


if __name__ == '__main__':
    main()
