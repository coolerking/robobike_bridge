#!/usr/bin/env python3
"""
ファイル名: convert_bag.py

record_session で記録した ros2 bag を LeRobotDataset に変換します(PC上の venv で実行)。

    - エピソード: robobike_episode の start〜end(ゲームパッドの START〜BACK/LB/切断)
    - フレーム: エピソード区間を POLICY_FPS の等間隔で区切り、各時刻以前の最新の
      画像・テレメトリ・ステータスを対応させる(時刻は bag の記録時刻=Pi上の受信時刻)
    - 行動: その時刻以前に最後に送信された bt_Str_S の value(未送信なら0)と、その時刻の mot_spd

入出力・正規化の定義は bridge.policy_features を使います。

実行例(リポジトリのトップで):
    source /opt/ros/lyrical/setup.bash && source install/setup.bash && source .venv/bin/activate
    python policy/convert_bag.py ~/robobike_data/raw/20261031_120000 --list
    python policy/convert_bag.py ~/robobike_data/raw/20261031_* --name course_v1 --exclude 2,5
"""
import argparse
import bisect
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

from bridge.constants import DATA_DATASETS_DIR
from bridge.constants import EPISODE_EVENT_END
from bridge.constants import EPISODE_EVENT_START
from bridge.constants import RECORD_STORAGE_ID
from bridge.constants import TOPICNAME_IMAGE
from bridge.constants import TOPICNAME_ROBOBIKE_COMMAND
from bridge.constants import TOPICNAME_ROBOBIKE_EPISODE
from bridge.constants import TOPICNAME_ROBOBIKE_STATUS
from bridge.constants import TOPICNAME_ROBOBIKE_TELEMETRY
from bridge.policy_features import FEATURE_ACTION
from bridge.policy_features import FEATURE_IMAGE
from bridge.policy_features import FEATURE_STATE
from bridge.policy_features import POLICY_FPS
from bridge.policy_features import STEER_COMMAND_NAME
from bridge.policy_features import build_action
from bridge.policy_features import build_state
from bridge.policy_features import decode_image
from bridge.policy_features import get_lerobot_features
from bridge.robobike_utils import get_command_index

# データセットのタスク説明(LeRobotDataset の各フレームに必須)
DEFAULT_TASK = 'Steer ROBOBIKE along the course'
# データセットの robot_type
ROBOT_TYPE = 'robobike'
# この時間(秒)より古い画像・テレメトリ・ステータスを使ったフレームは警告を出す
STALE_WARNING_SEC = 0.5

NSEC_PER_SEC = 1_000_000_000


@dataclass
class TimeSeries:
    """記録時刻(ナノ秒)順に並んだメッセージ列。"""
    times: list[int] = field(default_factory=list)
    values: list[Any] = field(default_factory=list)

    def append(self, time_ns: int, value: Any) -> None:
        self.times.append(time_ns)
        self.values.append(value)

    def latest(self, time_ns: int) -> Optional[tuple[int, Any]]:
        """time_ns 以前で最新の (記録時刻, 値) を返します(なければ None)。"""
        index = bisect.bisect_right(self.times, time_ns) - 1
        if index < 0:
            return None
        return self.times[index], self.values[index]


@dataclass
class Session:
    """1つの bag から読み込んだデータ。"""
    path: Path
    images: TimeSeries = field(default_factory=TimeSeries)
    telemetry: TimeSeries = field(default_factory=TimeSeries)
    status: TimeSeries = field(default_factory=TimeSeries)
    steer: TimeSeries = field(default_factory=TimeSeries)
    episode_events: TimeSeries = field(default_factory=TimeSeries)
    last_time_ns: int = 0


@dataclass
class Episode:
    """変換対象のエピソード区間。"""
    number: int
    session: Session
    start_ns: int
    end_ns: int
    end_reason: str


def read_session(path: Path) -> Session:
    """
    bag を読み込み、トピックごとの時系列に振り分けます。

    Args:
        path (Path): bag ディレクトリ

    Returns:
        Session: 読み込んだデータ
    """
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(path), storage_id=RECORD_STORAGE_ID),
        rosbag2_py.ConverterOptions(input_serialization_format='', output_serialization_format='')
    )
    message_types = {
        topic.name: get_message(topic.type) for topic in reader.get_all_topics_and_types()
    }
    steer_command_index = get_command_index(STEER_COMMAND_NAME)
    session = Session(path=path)
    while reader.has_next():
        # (トピック名, データ, 受信時刻, 送信時刻)：同一マシンで記録するため受信時刻を使う
        topic, data, time_ns, _ = reader.read_next_ext()
        topic = topic.lstrip('/')
        session.last_time_ns = max(session.last_time_ns, time_ns)
        if topic not in (
            TOPICNAME_IMAGE, TOPICNAME_ROBOBIKE_TELEMETRY, TOPICNAME_ROBOBIKE_STATUS,
            TOPICNAME_ROBOBIKE_COMMAND, TOPICNAME_ROBOBIKE_EPISODE,
        ):
            continue
        msg = deserialize_message(data, message_types['/' + topic])
        if topic == TOPICNAME_IMAGE:
            # 展開は使うフレームだけ後で行う
            session.images.append(time_ns, bytes(msg.data))
            continue
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            print(f'  warning: invalid JSON on {topic}: {msg.data!r}', file=sys.stderr)
            continue
        if topic == TOPICNAME_ROBOBIKE_TELEMETRY:
            session.telemetry.append(time_ns, payload)
        elif topic == TOPICNAME_ROBOBIKE_STATUS:
            session.status.append(time_ns, payload)
        elif topic == TOPICNAME_ROBOBIKE_COMMAND:
            if payload.get('command_index') == steer_command_index:
                session.steer.append(time_ns, payload.get('value'))
        elif topic == TOPICNAME_ROBOBIKE_EPISODE:
            session.episode_events.append(time_ns, payload)
    return session


def find_episodes(session: Session, first_number: int) -> list[Episode]:
    """
    エピソードイベントからエピソード区間を求めます。

    start が続いた場合は次の start で区切り、end がないまま bag が終わった場合は
    bag の最終時刻で区切ります。

    Args:
        session (Session): 読み込んだデータ
        first_number (int): 最初のエピソードに振る番号

    Returns:
        list[Episode]: エピソード区間のリスト
    """
    episodes: list[Episode] = []
    start_ns: Optional[int] = None

    def close(end_ns: int, reason: str) -> None:
        nonlocal start_ns
        if start_ns is not None:
            episodes.append(Episode(first_number + len(episodes), session, start_ns, end_ns, reason))
            start_ns = None

    for time_ns, event in zip(session.episode_events.times, session.episode_events.values):
        if event.get('event') == EPISODE_EVENT_START:
            close(time_ns, 'restart')
            start_ns = time_ns
        elif event.get('event') == EPISODE_EVENT_END:
            close(time_ns, str(event.get('reason', '')))
    close(session.last_time_ns, 'bag_end')
    return episodes


def iter_frames(episode: Episode):
    """
    エピソード区間を POLICY_FPS の等間隔で区切ったフレームを返します。

    画像・テレメトリ・ステータスが揃う前の時刻は飛ばします。

    Yields:
        tuple[dict, float]: (LeRobotDataset 用のフレーム辞書(task なし), 使用データの最大経過秒)
    """
    session = episode.session
    step_ns = NSEC_PER_SEC // POLICY_FPS
    time_ns = episode.start_ns
    while time_ns <= episode.end_ns:
        image = session.images.latest(time_ns)
        telemetry = session.telemetry.latest(time_ns)
        status = session.status.latest(time_ns)
        if image is not None and telemetry is not None and status is not None:
            steer = session.steer.latest(time_ns)
            max_age = max(time_ns - image[0], time_ns - telemetry[0], time_ns - status[0])
            yield {
                FEATURE_IMAGE: decode_image(image[1]),
                FEATURE_STATE: build_state(telemetry[1], status[1]),
                FEATURE_ACTION: build_action(None if steer is None else steer[1], status[1]),
            }, max_age / NSEC_PER_SEC
        time_ns += step_ns


def count_frames(episode: Episode) -> int:
    """エピソードの概算フレーム数を返します(一覧表示用)。"""
    return int((episode.end_ns - episode.start_ns) * POLICY_FPS // NSEC_PER_SEC) + 1


def parse_exclude(text: str) -> set[int]:
    """'2,5' 形式の除外エピソード番号を解析します。"""
    return {int(item) for item in text.split(',') if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='convert_bag',
        description='Convert ROBOBIKE ros2 bags to a LeRobotDataset'
    )
    parser.add_argument('bags', nargs='+', type=Path, help='bag directories recorded by record_session')
    parser.add_argument('--name', help='dataset name (saved under DATA_DATASETS_DIR/<name>)')
    parser.add_argument('--list', action='store_true', help='list episodes and exit')
    parser.add_argument('--exclude', type=parse_exclude, default=set(),
                        help='comma separated episode numbers to exclude (see --list)')
    parser.add_argument('--task', default=DEFAULT_TASK, help=f'task description (default: {DEFAULT_TASK!r})')
    parser.add_argument('--overwrite', action='store_true', help='overwrite an existing dataset')
    args = parser.parse_args()

    # bag を読み込んでエピソードを列挙する(番号は全 bag を通した連番)
    episodes: list[Episode] = []
    for bag in args.bags:
        print(f'reading {bag} ...')
        session = read_session(bag)
        episodes += find_episodes(session, first_number=len(episodes) + 1)

    print(f'\n{"No":>3}  {"bag":<20} {"start":>8} {"sec":>6} {"frames":>6}  end_reason')
    for episode in episodes:
        mark = '  (excluded)' if episode.number in args.exclude else ''
        offset_sec = (episode.start_ns - episode.session.images.times[0]) / NSEC_PER_SEC \
            if episode.session.images.times else 0.0
        print(
            f'{episode.number:>3}  {episode.session.path.name:<20} {offset_sec:>8.1f} '
            f'{(episode.end_ns - episode.start_ns) / NSEC_PER_SEC:>6.1f} {count_frames(episode):>6}  '
            f'{episode.end_reason}{mark}'
        )
    if args.list:
        return
    if args.name is None:
        parser.error('--name is required unless --list is specified')

    targets = [episode for episode in episodes if episode.number not in args.exclude]
    if not targets:
        print('no episodes to convert', file=sys.stderr)
        sys.exit(1)

    root = DATA_DATASETS_DIR / args.name
    if root.exists():
        if not args.overwrite:
            print(f'{root} already exists (use --overwrite)', file=sys.stderr)
            sys.exit(1)
        shutil.rmtree(root)

    # LeRobot は import に時間がかかるため必要になってから読み込む
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    dataset = LeRobotDataset.create(
        repo_id=f'local/{args.name}',
        fps=POLICY_FPS,
        features=get_lerobot_features(),
        root=root,
        robot_type=ROBOT_TYPE,
        use_videos=True,
    )
    for episode in targets:
        frames = 0
        stale = 0
        for frame, age_sec in iter_frames(episode):
            frame['task'] = args.task
            dataset.add_frame(frame)
            frames += 1
            stale += age_sec > STALE_WARNING_SEC
        if frames == 0:
            print(f'episode {episode.number}: no frames (missing image/telemetry/status), skipped')
            dataset.clear_episode_buffer()
            continue
        dataset.save_episode()
        warning = f', {stale} frame(s) used data older than {STALE_WARNING_SEC} s' if stale else ''
        print(f'episode {episode.number}: saved {frames} frames{warning}')
    dataset.finalize()
    print(f'\ndataset saved to {root}')


if __name__ == '__main__':
    main()
