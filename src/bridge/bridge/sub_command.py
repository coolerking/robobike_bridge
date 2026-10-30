#!/usr/bin/env python3
"""
ファイル名: sub_command.py


TOPICNAME_ROBOBIKE_COMMAND トピックを受信したら、
その内容をROBOBIKE操作系コマンドにして、
Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth にWiFi接続されたROBOBIKEに対して操作系のコマンドを送信する。

ROBOBIKEへのHTTP送信は受信コールバックとは別の送信スレッドで行うため、
通信待ちの間も受信は止まらない。未送信のコマンドは次の規則で整理する。
    - 停止系コマンド(ROBOBIKE_STOP_COMMAND_NAMES): 未送信のコマンドをすべて破棄して最優先で送信
    - value値を持つコマンド(操舵など): 未送信の同じコマンドを最新の値で置き換え
    - その他: 受信順に送信
停止系コマンドの送信に失敗した場合は最大 STOP_COMMAND_MAX_RETRIES 回まで再送する
(新しい停止系コマンドが届いた場合は再送をやめてそちらを送信する)。

実行例:
    ros2 run bridge sub_command --dummy --ros-args -r __node:=bike_test # ダミーデータでの実行
    ros2 run bridge sub_command --ros-args -r __node:=bike_test # 実機データでの実行
"""
import sys
import json
import time
import argparse
import math
import threading
from collections import deque
from typing import Optional
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from rclpy.utilities import remove_ros_args
from .robobike_bridge import RobobikeBridge

from .constants import QOS_PROFILE
from .constants import ROBOBIKE_DUMMY_IP
from .constants import ROBOBIKE_STOP_COMMAND_NAMES
from .constants import TOPICNAME_ROBOBIKE_COMMAND
from .pub_command import CommandPublisher
from .robobike_utils import get_command_name
from .robobike_utils import normalize_value

# 未送信コマンドの最大保持数(超えた場合は古いものから破棄)
MAX_PENDING_COMMANDS = 20
# 停止系コマンド送信失敗時の最大再送回数(停止系コマンドは何度送っても結果が同じため再送できる)
STOP_COMMAND_MAX_RETRIES = 3


class PendingCommand:
    """送信待ちのROBOBIKE操作系コマンド。"""

    def __init__(self, command: str, value: Optional[int]) -> None:
        self.command = command
        self.value = value
        # 受信時刻(送信までの待ち時間の計測用)
        self.received_at = time.monotonic()


class RobobikeCommandSubscriber(Node):
    """
    ROBOBIKEへ操作系コマンドを送信するROS2ノードクラス。

    TOPICNAME_ROBOBIKE_COMMAND トピックを購読し、
    受信した内容をROBOBIKE操作系コマンドに変換して送信スレッドに渡す。
    """
    def __init__(self, test:bool=False):
        """
        RobobikeCommandSubscriber クラスの初期化処理

        ROS2 Subscriber と送信スレッドの初期化を行います。

        Args:
            test (bool): ダミーデータを使用するかどうか
        """
        super().__init__('robobike_command_subscriber_node')

        if test:
            self.broker = RobobikeBridge(ROBOBIKE_DUMMY_IP)
        else:
            self.broker = RobobikeBridge()

        # 送信待ちキューと送信スレッド
        self._pending: deque[PendingCommand] = deque()
        self._condition = threading.Condition()
        self._running = True
        self._sender = threading.Thread(target=self._send_loop, daemon=True)
        self._sender.start()

        self.subscription = self.create_subscription(
            String,
            TOPICNAME_ROBOBIKE_COMMAND,
            self.receive_command,
            QOS_PROFILE
        )

        self.get_logger().info('RobobikeCommandSubscriber initialized successfully.')

    def receive_command(self, msg: String) -> None:
        """
        受信した操作系コマンドを検証し、送信待ちキューに追加します。

        HTTP送信は送信スレッドで行うため、このコールバックはすぐに戻ります。

        Args:
            msg (std_msgs.msg.String): 受信した操作系コマンドのメッセージ
        """
        try:
            self.get_logger().info(f'Received command: {msg.data}')
            command_dict = json.loads(msg.data)
            if not isinstance(command_dict, dict):
                raise ValueError('Command payload must be a JSON object')

            command_index = command_dict.get('command_index')
            if isinstance(command_index, bool) or not isinstance(command_index, int):
                raise ValueError('command_index must be an integer')
            command = get_command_name(command_index)

            value: Optional[int] = None
            if CommandPublisher.need_value(command_index):
                raw_value = command_dict.get('value')
                if raw_value is None:
                    raise ValueError(f'Command {command} requires a value')
                if isinstance(raw_value, bool):
                    raise ValueError('Command value must be numeric')
                float_value = float(raw_value)
                if not math.isfinite(float_value):
                    raise ValueError(f'Command value must be finite: {raw_value}')
                # 整数に丸めて範囲内に収める
                value = normalize_value(float_value)
            elif command_dict.get('value') is not None:
                # value値を使わないコマンドの値は送信しない
                self.get_logger().debug(f'Ignoring value for command {command}')

            self._enqueue(PendingCommand(command, value))
        except Exception as e:
            self.get_logger().error(f'Error processing command: {e}')

    def _enqueue(self, pending: PendingCommand) -> None:
        """
        送信待ちキューにコマンドを追加します。

        Args:
            pending (PendingCommand): 追加するコマンド
        """
        with self._condition:
            if pending.command in ROBOBIKE_STOP_COMMAND_NAMES:
                # 停止系コマンドは未送信のコマンドをすべて破棄して最優先にする
                if self._pending:
                    self.get_logger().warning(
                        f'Discarding {len(self._pending)} pending command(s) '
                        f'for stop command {pending.command}'
                    )
                self._pending.clear()
            elif pending.value is not None:
                # value値を持つコマンドは未送信の同じコマンドを最新値で置き換える
                for index, queued in enumerate(self._pending):
                    if queued.command == pending.command:
                        del self._pending[index]
                        break
            if len(self._pending) >= MAX_PENDING_COMMANDS:
                dropped = self._pending.popleft()
                self.get_logger().warning(f'Pending queue full; dropped {dropped.command}')
            self._pending.append(pending)
            self._condition.notify()

    def _send_loop(self) -> None:
        """送信スレッド本体。キューからコマンドを取り出してROBOBIKEに送信します。"""
        while True:
            with self._condition:
                while self._running and not self._pending:
                    self._condition.wait()
                if not self._running:
                    return
                pending = self._pending.popleft()
            self._send(pending)

    def _has_pending_stop_command(self) -> bool:
        """未送信の停止系コマンドがあるかを返します。"""
        with self._condition:
            return any(
                queued.command in ROBOBIKE_STOP_COMMAND_NAMES for queued in self._pending
            )

    def _send(self, pending: PendingCommand) -> None:
        """
        コマンドをROBOBIKEに送信し、待ち時間と通信時間をログに出力します。

        停止系コマンドの送信に失敗した場合は最大 STOP_COMMAND_MAX_RETRIES 回まで再送します。
        ただし新しい停止系コマンドが届いている場合は再送をやめ、そちらの送信に任せます。
        停止系以外のコマンドは結果が変わる(速度+1など)可能性があるため再送しません。

        Args:
            pending (PendingCommand): 送信するコマンド
        """
        is_stop = pending.command in ROBOBIKE_STOP_COMMAND_NAMES
        max_attempts = 1 + (STOP_COMMAND_MAX_RETRIES if is_stop else 0)
        wait_ms = (time.monotonic() - pending.received_at) * 1000
        for attempt in range(1, max_attempts + 1):
            started_at = time.monotonic()
            try:
                result = self.broker.send_command(pending.command, pending.value)
                error = result.get('error', 'Unknown error') if result.get('status') == 'error' else None
            except Exception as e:
                error = str(e)
            http_ms = (time.monotonic() - started_at) * 1000

            if error is None:
                self.get_logger().info(
                    f'Sent command: {pending.command}, value: {pending.value} '
                    f'(wait: {wait_ms:.1f} ms, http: {http_ms:.1f} ms, attempt: {attempt})'
                )
                return

            if attempt < max_attempts:
                if self._has_pending_stop_command():
                    self.get_logger().warning(
                        f'Failed to send command {pending.command}: {error} '
                        f'(http: {http_ms:.1f} ms); newer stop command is pending, skipping retry'
                    )
                    return
                self.get_logger().warning(
                    f'Failed to send command {pending.command}: {error} '
                    f'(http: {http_ms:.1f} ms); retrying ({attempt}/{STOP_COMMAND_MAX_RETRIES})'
                )
            else:
                self.get_logger().error(
                    f'Failed to send command {pending.command}: {error} '
                    f'(wait: {wait_ms:.1f} ms, http: {http_ms:.1f} ms, attempt: {attempt})'
                )

    def destroy_node(self) -> None:
        """送信スレッドを停止してからROSノードを破棄します。"""
        with self._condition:
            self._running = False
            self._condition.notify()
        # 送信中のHTTP通信はタイムアウトまで待つ可能性があるため上限を設ける
        self._sender.join(timeout=2.0)
        super().destroy_node()


def main():
    """
    メイン関数

    TOPICNAME_ROBOBIKE_COMMAND トピックを購読して、ROBOBIKE操作系コマンドを処理するノードを起動します。
    Ctrl+C を押すと終了します。
    """
    parser = argparse.ArgumentParser(
        prog="sub_command",
        description="Subscribe ROBOBIKE commands and send them to the bike"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy data instead of the real ROBOBIKE')
    app_args = remove_ros_args(args=sys.argv)[1:]
    args = parser.parse_args(app_args)

    print(f'[main] start subscriber test:{str(args.dummy)}')
    rclpy.init()
    node: Optional[RobobikeCommandSubscriber] = None
    try:
        node = RobobikeCommandSubscriber(test=args.dummy)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        print('[main] Interrupt received')
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()
        print('[main] subscriber shutdown')

if __name__ == '__main__':
    main()
