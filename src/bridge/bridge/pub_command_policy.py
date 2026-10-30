"""
学習済み方策(LeRobot ACT)の出力をROBOBIKEコマンドとしてpublishするノード(PC の .venv で実行)。

俯瞰カメラ画像・テレメトリ・ステータスを購読し、制御周期(POLICY_CONTROL_INTERVAL_SEC)ごとに
推論して操舵コマンド(bt_Str_S)を送信します。速度(mot_spd)はゲームパッドで人が操作します。

    - ゲームパッドの START(エピソード開始)で操舵を開始し、BACK/LB(エピソード終了)で停止します
      (--autostart の場合は起動直後から操舵します)
    - 推論が成功するたびに方策ハートビートを送信します。sub_command を --watchdog 付きで
      起動すると、入力が途絶えたり推論が止まった場合に緊急停止します
      (操舵中に入力が途絶えた場合は操舵も停止し、再開には START が必要です)
    - 前回送信値から POLICY_STEER_CHANGE_THRESHOLD 以上変化した場合のみ操舵コマンドを送信します

lerobot・torch が必要なため、colcon でビルドした bridge を .venv の Python で実行します。

実行例(リポジトリのトップで):
    source /opt/ros/lyrical/setup.bash && source install/setup.bash
    .venv/bin/python -m bridge.pub_command_policy \\
        --model ~/robobike_data/runs/<実行名>/checkpoints/last/pretrained_model
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.signals import SignalHandlerOptions
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Header
from std_msgs.msg import String

from .constants import EPISODE_EVENT_END
from .constants import EPISODE_EVENT_START
from .constants import HEARTBEAT_QOS_PROFILE
from .constants import IMAGE_QOS_PROFILE
from .constants import POLICY_CONTROL_INTERVAL_SEC
from .constants import POLICY_DEFAULT_N_ACTION_STEPS
from .constants import POLICY_INPUT_TIMEOUT_SEC
from .constants import POLICY_STEER_CHANGE_THRESHOLD
from .constants import QOS_PROFILE
from .constants import TOPICNAME_IMAGE
from .constants import TOPICNAME_POLICY_HEARTBEAT
from .constants import TOPICNAME_ROBOBIKE_EPISODE
from .constants import TOPICNAME_ROBOBIKE_STATUS
from .constants import TOPICNAME_ROBOBIKE_TELEMETRY
from .policy_features import FEATURE_IMAGE
from .policy_features import FEATURE_STATE
from .policy_features import STEER_COMMAND_NAME
from .policy_features import action_to_steer_value
from .policy_features import build_state
from .policy_features import decode_image
from .pub_command import CommandPublisher
from .robobike_utils import get_command_index

# 入力待ちなどの警告ログの最短間隔(秒)
WARNING_THROTTLE_SEC = 2.0


class PolicyCommandPublisher(CommandPublisher):
    """方策の推論結果を操舵コマンドとして送信するPublisher。"""

    def __init__(
        self,
        policy: Any,
        preprocessor: Any,
        postprocessor: Any,
        autostart: bool = False,
        node_name: str = 'policy_command_publisher'
    ):
        """
        Args:
            policy (Any): 評価モードの ACTPolicy(act_loader.load_act_policy の戻り値)
            preprocessor (Any): 前処理パイプライン
            postprocessor (Any): 後処理パイプライン
            autostart (bool): True の場合はエピソード開始を待たずに操舵を開始する
            node_name (str): ROSノード名
        """
        super().__init__(node_name)
        self.policy = policy
        self.preprocessor = preprocessor
        self.postprocessor = postprocessor

        # 最新の入力と受信時刻(time.monotonic())
        self._image: Optional[np.ndarray] = None
        self._image_time = 0.0
        self._telemetry: Optional[dict] = None
        self._telemetry_time = 0.0
        self._status: Optional[dict] = None
        self._status_time = 0.0
        # 最後に送信した操舵値(None は未送信)
        self._last_steer_value: Optional[int] = None
        # 操舵開始後に推論できたか(開始直後の入力待ちと、操舵中の入力途絶を区別する)
        self._has_inferred = False
        self._last_warning_time = 0.0

        self.create_subscription(
            CompressedImage, TOPICNAME_IMAGE, self.receive_image, IMAGE_QOS_PROFILE)
        self.create_subscription(
            String, TOPICNAME_ROBOBIKE_TELEMETRY, self.receive_telemetry, QOS_PROFILE)
        self.create_subscription(
            String, TOPICNAME_ROBOBIKE_STATUS, self.receive_status, QOS_PROFILE)
        self.create_subscription(
            String, TOPICNAME_ROBOBIKE_EPISODE, self.receive_episode, QOS_PROFILE)
        self.heartbeat_publisher = self.create_publisher(
            Header,
            TOPICNAME_POLICY_HEARTBEAT,
            HEARTBEAT_QOS_PROFILE
        )

        if autostart:
            self.start_policy()
        self.timer = self.create_timer(POLICY_CONTROL_INTERVAL_SEC, self.control_step)

    def receive_image(self, msg: CompressedImage) -> None:
        """俯瞰カメラ画像を受信して方策入力用に展開します。"""
        try:
            self._image = decode_image(bytes(msg.data))
            self._image_time = time.monotonic()
        except ValueError as error:
            self.get_logger().warning(f'Invalid image: {error}')

    def receive_telemetry(self, msg: String) -> None:
        """テレメトリを受信します。"""
        self._telemetry = self._parse_json(msg, 'telemetry')
        if self._telemetry is not None:
            self._telemetry_time = time.monotonic()

    def receive_status(self, msg: String) -> None:
        """ステータスを受信します。"""
        self._status = self._parse_json(msg, 'status')
        if self._status is not None:
            self._status_time = time.monotonic()

    def receive_episode(self, msg: String) -> None:
        """エピソード開始/終了イベントで操舵を開始/停止します。"""
        event = self._parse_json(msg, 'episode')
        if event is None:
            return
        if event.get('event') == EPISODE_EVENT_START:
            self.start_policy()
        elif event.get('event') == EPISODE_EVENT_END:
            self.stop_policy()

    def _parse_json(self, msg: String, name: str) -> Optional[dict]:
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as error:
            self.get_logger().warning(f'Invalid {name} JSON: {error}')
            return None
        return data if isinstance(data, dict) else None

    def start_policy(self) -> None:
        """方策による操舵を開始します(予測済みの行動列は破棄する)。"""
        self.policy.reset()
        self._last_steer_value = None
        self._has_inferred = False
        self.start_pub()
        self.get_logger().info('Policy steering started.')

    def stop_policy(self) -> None:
        """方策による操舵を停止します(停止コマンドはゲームパッド側で送信する)。"""
        if self.can_publish():
            self.get_logger().info('Policy steering stopped.')
        self.stop_pub()

    def _warn_throttled(self, message: str) -> None:
        now = time.monotonic()
        if now - self._last_warning_time >= WARNING_THROTTLE_SEC:
            self.get_logger().warning(message)
            self._last_warning_time = now

    def _get_stale_inputs(self) -> list[str]:
        """有効期間を過ぎた(または未受信の)入力名の一覧を返します。"""
        now = time.monotonic()
        inputs = [
            ('image', self._image, self._image_time),
            ('telemetry', self._telemetry, self._telemetry_time),
            ('status', self._status, self._status_time),
        ]
        return [
            name for name, value, received in inputs
            if value is None or now - received > POLICY_INPUT_TIMEOUT_SEC
        ]

    def control_step(self) -> None:
        """
        制御周期ごとの処理。

        ハートビートは推論が完了した後に送信する
        (入力が途絶えたり推論が止まった場合にウォッチドッグが検知できるようにするため)。
        """
        stale = self._get_stale_inputs()
        if stale:
            # 古い入力から予測した行動列を使い続けないよう破棄する
            self.policy.reset()
            if self.can_publish() and self._has_inferred:
                # ウォッチドッグが緊急停止するため、入力が復帰しても操舵を再開しない
                # (再開はゲームパッドの START で行う)
                self.get_logger().error(
                    f'Inputs lost during steering: {", ".join(stale)}; stopping policy steering.')
                self.stop_policy()
            else:
                self._warn_throttled(f'Waiting for inputs: {", ".join(stale)}')
            return

        try:
            steer_value = self.infer_steer_value()
        except Exception as error:
            self.policy.reset()
            self._warn_throttled(f'Inference failed: {type(error).__name__}: {error}')
            return

        if self.can_publish() and (
            self._last_steer_value is None
            or abs(steer_value - self._last_steer_value) >= POLICY_STEER_CHANGE_THRESHOLD
        ):
            self.send_command({
                'command_index': get_command_index(STEER_COMMAND_NAME),
                'value': steer_value,
            })
            self._last_steer_value = steer_value
        self._has_inferred = True
        self.send_heartbeat()

    def infer_steer_value(self) -> int:
        """
        最新の入力から推論して操舵値を返します。

        Returns:
            int: bt_Str_S の value(-100〜100)
        """
        import torch

        assert self._image is not None and self._telemetry is not None and self._status is not None
        state = build_state(self._telemetry, self._status)
        image = torch.from_numpy(self._image).permute(2, 0, 1).float() / 255.0
        batch = {
            FEATURE_IMAGE: image,
            FEATURE_STATE: torch.from_numpy(state),
        }
        with torch.inference_mode():
            action = self.postprocessor(self.policy.select_action(self.preprocessor(batch)))
        return action_to_steer_value(action.squeeze(0).cpu().numpy())

    def send_heartbeat(self) -> None:
        """方策ハートビートを送信します。"""
        msg = Header()
        msg.stamp = self.get_clock().now().to_msg()
        msg.frame_id = self.get_name()
        self.heartbeat_publisher.publish(msg)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='pub_command_policy',
        description='Publish ROBOBIKE steering commands from a trained ACT policy'
    )
    parser.add_argument(
        '--model',
        required=True,
        type=Path,
        help='pretrained_model directory (contains config.json and model.safetensors)')
    parser.add_argument(
        '--device',
        default=None,
        help='Inference device such as cuda or cpu (default: the training setting)')
    parser.add_argument(
        '--n_action_steps',
        type=int,
        default=POLICY_DEFAULT_N_ACTION_STEPS,
        help='Number of predicted steps executed before the next inference '
             f'(default: {POLICY_DEFAULT_N_ACTION_STEPS})')
    parser.add_argument(
        '--autostart',
        action='store_true',
        help='Start steering immediately without waiting for an episode start (for testing)')
    args = parser.parse_args(remove_ros_args(args=sys.argv)[1:])

    # lerobot・torch の読み込みに時間がかかるため、引数の確認後に import する
    import torch
    from .act_loader import load_act_policy
    # 推論の合間も CPU スレッドが待機ループで回り続け CPU を数コア分使うため 1 スレッドにする
    # (GPU 推論では遅くならない。計測: 364% → 5%、1ステップ平均 6.4ms → 4.6ms)
    torch.set_num_threads(1)
    print(f'[main] loading policy: {args.model}')
    policy, preprocessor, postprocessor = load_act_policy(
        args.model.expanduser(), device=args.device, n_action_steps=args.n_action_steps)
    print(f'[main] policy loaded on {policy.config.device}')

    # Ctrl+C 後も destroy_node で停止コマンドを送信できるよう、シグナル処理は自前で行う
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node: Optional[PolicyCommandPublisher] = None
    try:
        node = PolicyCommandPublisher(
            policy, preprocessor, postprocessor, autostart=args.autostart)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()


if __name__ == '__main__':
    main()
