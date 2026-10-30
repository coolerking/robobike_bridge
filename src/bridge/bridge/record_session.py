#!/usr/bin/env python3
"""
ファイル名: record_session.py

学習データ収集用に RECORD_TOPICS を ros2 bag で記録します。
データ収集1回(セッション)を1つの bag に記録し、エピソードの区切りは
ゲームパッドの START/BACK で送信される TOPICNAME_ROBOBIKE_EPISODE トピックで判別します。

保存先は DATA_RAW_DIR/<YYYYmmdd_HHMMSS>/ です(環境変数 ROBOBIKE_DATA_DIR で変更可)。
カメラ・ROBOBIKE通信・ゲームパッドと同じ Raspberry Pi 上で実行してください
(各トピックにはPublish時刻がないため、受信時刻=記録時刻を基準に同期します)。

実行例:
    ros2 run bridge record_session # Ctrl+C で記録終了
"""
import os
import shutil
import sys
from datetime import datetime

from .constants import DATA_RAW_DIR
from .constants import RECORD_STORAGE_ID
from .constants import RECORD_TOPICS


def main() -> None:
    """ros2 bag record を起動します(このプロセスを置き換えるため Ctrl+C は ros2 bag が処理する)。"""
    ros2 = shutil.which('ros2')
    if ros2 is None:
        print('ros2 command not found; source /opt/ros/<distro>/setup.bash first.', file=sys.stderr)
        sys.exit(1)
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_dir = DATA_RAW_DIR / datetime.now().strftime('%Y%m%d_%H%M%S')
    command = [
        ros2, 'bag', 'record',
        '--storage', RECORD_STORAGE_ID,
        '--output', str(output_dir),
        # ros2 bag record は先頭に / のない相対名では記録しないため絶対名にする
        '--topics', *[f'/{topic}' for topic in RECORD_TOPICS],
    ]
    print(f'[main] recording to {output_dir}')
    print(f'[main] topics: {" ".join(RECORD_TOPICS)}')
    os.execv(ros2, command)


if __name__ == '__main__':
    main()
