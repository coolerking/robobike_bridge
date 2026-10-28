"""
ファイル名：constants.py

ROS2 bridge パッケージ内の定数を定義するファイル
"""
from typing import Final
from rclpy.qos import QoSProfile

"""デバッグフラグ"""
DEBUG: Final[bool] = True

"""トピック名(カメラ画像用)"""
TOPICNAME_IMAGE: Final[str] = 'camera_image'

"""QoS設定"""
QOS_PROFILE: Final[QoSProfile] = QoSProfile(depth=10)

## Camera Image関連
IMAGE_ENCODING_TYPE: Final[str] = 'bgr8'
CAMERA_DEV_LETTER: Final[int] = 0  # /dev/video0

## Publish間隔
PUBLISH_INTERVAL_SEC: Final[float] = 0.05