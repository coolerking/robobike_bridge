"""
ファイル名: policy_features.py

方策(LeRobot ACT)の入出力の定義と変換処理です。
データセット変換(policy/convert_bag.py)・学習・推論(pub_command_policy)で
同じ定義を使うため、torch に依存しない形でここにまとめます。

    observation.images.overhead: 俯瞰カメラ画像(IMAGE_HEIGHT x IMAGE_WIDTH x 3, RGB, uint8)
    observation.state:           STATE_NAMES の float32 ベクトル(テレメトリ＋ステータス)
    action:                      ACTION_NAMES の float32 ベクトル(操舵値＋速度設定値)

行動のうち推論時に使うのは操舵値(steer)のみで、速度(mot_spd)はゲームパッドで人が操作する。
mot_spd を行動に含めるのは、LeRobotDataset が shape (1,) の特徴量をスカラーとして保存し
ACT で扱えなくなるのを避けるためと、将来の速度制御への拡張のため。
"""
from typing import Final, Mapping, Optional

import cv2
import numpy as np

from .constants import IMAGE_HEIGHT
from .constants import IMAGE_WIDTH
from .constants import POLICY_CONTROL_INTERVAL_SEC
from .constants import ROBOBIKE_VALUE_MAX
from .robobike_utils import normalize_value

# データセットのフレームレート(制御周期と同じ)
POLICY_FPS: Final[int] = round(1.0 / POLICY_CONTROL_INTERVAL_SEC)

# 画像の特徴量名
FEATURE_IMAGE: Final[str] = 'observation.images.overhead'
# 状態の特徴量名
FEATURE_STATE: Final[str] = 'observation.state'
# 行動の特徴量名
FEATURE_ACTION: Final[str] = 'action'

# 状態に使うテレメトリ項目(get_acc、ウィンドウ平均値)
STATE_TELEMETRY_NAMES: Final[list[str]] = [
    'drv',       # モータ出力
    'str',       # ステアリング出力(ROBOBIKE側のバランス制御を含む)
    'std',       # スタンド出力
    'sv_pos',    # ステアリングサーボ位置(-90〜+90)
    'gy_roll',   # ジャイロロール角速度
    'gy_yaw',    # ジャイロヨー角速度
    'gy_pitch',  # ジャイロピッチ角速度
    'acc_x',     # 加速度X軸
    'acc_y',     # 加速度Y軸
    'acc_z',     # 加速度Z軸
]
# 状態に使うステータス項目(only_data)
STATE_STATUS_NAMES: Final[list[str]] = [
    'mot_spd',   # モータ速度設定値(走行中にゲームパッドで増減する)
]
# 状態ベクトルの項目名(この順に並べる)
STATE_NAMES: Final[list[str]] = STATE_TELEMETRY_NAMES + STATE_STATUS_NAMES

# 行動ベクトルの項目名
ACTION_NAMES: Final[list[str]] = [
    'steer',     # bt_Str_S の value(-100〜100)を -1.0〜1.0 に正規化した値
    'mot_spd',   # モータ速度設定値(推論時は使用しない)
]

# 操舵コマンド名(行動の送信に使う)
STEER_COMMAND_NAME: Final[str] = 'bt_Str_S'


def get_lerobot_features() -> dict:
    """
    LeRobotDataset.create() に渡す features 定義を返します。

    Returns:
        dict: 特徴量名をキーとする定義の辞書
    """
    return {
        FEATURE_IMAGE: {
            'dtype': 'video',
            'shape': (IMAGE_HEIGHT, IMAGE_WIDTH, 3),
            'names': ['height', 'width', 'channels'],
        },
        FEATURE_STATE: {
            'dtype': 'float32',
            'shape': (len(STATE_NAMES),),
            'names': STATE_NAMES,
        },
        FEATURE_ACTION: {
            'dtype': 'float32',
            'shape': (len(ACTION_NAMES),),
            'names': ACTION_NAMES,
        },
    }


def decode_image(data: bytes) -> np.ndarray:
    """
    pub_image が送信した JPEG を方策入力用の RGB 画像に変換します。

    Args:
        data (bytes): CompressedImage.data

    Returns:
        np.ndarray: IMAGE_HEIGHT x IMAGE_WIDTH x 3 の RGB 画像(uint8)

    Raises:
        ValueError: 展開できない場合
    """
    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Failed to decode image')
    if frame.shape[1] != IMAGE_WIDTH or frame.shape[0] != IMAGE_HEIGHT:
        frame = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def build_state(
    telemetry: Mapping[str, object],
    status: Mapping[str, object]
) -> np.ndarray:
    """
    テレメトリとステータスから状態ベクトルを作成します。

    Args:
        telemetry (Mapping[str, object]): robobike_telemetry の JSON を辞書にしたもの
        status (Mapping[str, object]): robobike_status の JSON を辞書にしたもの

    Returns:
        np.ndarray: STATE_NAMES 順の float32 ベクトル

    Raises:
        KeyError: 必要な項目がない場合
        ValueError: 数値に変換できない場合
    """
    values = [float(telemetry[name]) for name in STATE_TELEMETRY_NAMES]  # type: ignore[arg-type]
    values += [float(status[name]) for name in STATE_STATUS_NAMES]  # type: ignore[arg-type]
    return np.asarray(values, dtype=np.float32)


def build_action(steer_value: Optional[float], status: Mapping[str, object]) -> np.ndarray:
    """
    操舵コマンドの value(-100〜100)とステータスから行動ベクトルを作成します。

    Args:
        steer_value (Optional[float]): bt_Str_S の value(未送信の場合は None で直進扱い)
        status (Mapping[str, object]): robobike_status の JSON を辞書にしたもの

    Returns:
        np.ndarray: ACTION_NAMES 順の float32 ベクトル

    Raises:
        KeyError: 必要な項目がない場合
        ValueError: 数値に変換できない場合
    """
    steer = 0.0 if steer_value is None else normalize_value(steer_value) / ROBOBIKE_VALUE_MAX
    return np.asarray([steer, float(status['mot_spd'])], dtype=np.float32)  # type: ignore[arg-type]


def action_to_steer_value(action: np.ndarray) -> int:
    """
    行動ベクトルの操舵値を操舵コマンドの value(-100〜100 の整数)に変換します。

    Args:
        action (np.ndarray): ACTION_NAMES 順のベクトル

    Returns:
        int: bt_Str_S の value
    """
    return normalize_value(float(action[0]) * ROBOBIKE_VALUE_MAX)
