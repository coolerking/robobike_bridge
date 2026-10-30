#!/usr/bin/env python3
"""
ファイル名: robobike_bridge.py

Raspberry Pi 5/Ubuntu Desktop 26.04 LTS/ROS2 Lyrical Luth のWiFi 接続された
Robobike との通信をブリッジするためのモジュールです。

基本的に別モジュールからRobobikeBridgeクラスを呼び出して使用します。
直接実行することで、疎通テストを行うことができます。

疎通テスト実行例：
    python3 -m bridge.robobike_bridge --dummy # ダミーデータでのテスト実行
    python3 -m bridge.robobike_bridge # 実機データでのテスト実行
"""
import csv
import time
import json
import argparse
import logging
import math
from http.client import IncompleteRead
from io import StringIO
from urllib.request import urlopen

# ROBOBIKE 実機 IPアドレス
from .constants import ROBOBIKE_DEFAULT_IP
# dummyserver IPアドレス
from .constants import ROBOBIKE_DUMMY_IP

# HTTP/GET command プレフィクス
from .constants import ROBOBIKE_COMMAND_PREFIX
# HTTP/GET value サフィックス(操舵角指定用)
from .constants import ROBOBIKE_VALUE_SUFFIX
# HTTP/GET get_acc プレフィクス
from .constants import ROBOBIKE_GET_ACC_PREFIX
# HTTP/GET clear_buffer プレフィクス
from .constants import ROBOBIKE_CLEAR_BUFFER_PREFIX

# ステータスデータ(command="only_data"戻り値)項目数
from .constants import ROBOBIKE_STATUS_CSV_INDEXES_LEN
# ステータスデータ(command="only_data"戻り値)の float 値の項目インデックス
from .constants import ROBOBIKE_STATUS_CSV_INDEXES_FLOAT
# ステータスデータ(command="only_data"戻り値)の int 値の項目インデックス
from .constants import ROBOBIKE_STATUS_CSV_INDEXES_INT
# ステータスデータ インデックス番号←→項目名の変換用関数
from .robobike_utils import get_command_index, get_status_name

# テレメトリデータ(get_acc戻り値)項目数
from .constants import ROBOBIKE_TELEMETRY_CSV_INDEXES_LEN
# テレメトリデータ(get_acc戻り値)の項目名リスト(すべて)
from .constants import ROBOBIKE_TELEMETRY_CSV_INDEXES
# テレメトリデータ(get_acc戻り値)の項目名リスト(float値のもの)
from .constants import ROBOBIKE_TELEMETRY_CSV_INDEXES_FLOAT
# テレメトリデータ(get_acc戻り値)の項目名リスト(int値のもの)
from .constants import ROBOBIKE_TELEMETRY_CSV_INDEXES_INT
# テレメトリデータとして有効な範囲（ミリ秒）：最新データの過去何ミリ秒まで有効か
from .constants import TELEMETRY_WINDOW_MSEC

# HTTP通信のタイムアウト時間(秒)
from .constants import HTTP_TIMEOUT_SEC

# ロガー設定
logger = logging.getLogger(__name__)

class RobobikeBridge():
    """
    Robobike 本番機とHTTP GET通信を行い、コマンド送信を行うためのブリッジクラス。
    """
    def __init__(self, default_ip=ROBOBIKE_DEFAULT_IP) -> None:
        """
        初期化メソッド。

        Args:
            default_ip (str, optional): Robobike の IP アドレス。指定しない場合はデフォルトの IP アドレスを使用。
        """
        self.robobike_base_url = f"http://{default_ip}"
        self._telemetry_history: list[dict[str, str | int | float]] = []
        self._latest_telemetry_time: int | None = None
        logger.info(f"Robobike base URL set to: {self.robobike_base_url}")

    def _get_command_url(self, button:str='only_data', value:float=None) -> str:
        """
        Robobike 本番機へのコマンド URL を生成します。

        Args:
            button (str): コマンド名(ROBOBIKE_COMMAND_NAMES に含まれるいずれかの要素)。デフォルトは 'only_data'。
            value (float, optional): ボタンに対応する値。指定しない場合は None。

        Returns:
            str: 生成されたコマンド URL。
        """
        # button に入っている文字列の配列インデックスを取得
        button_index = get_command_index(button)

        # コマンド URL を生成(value指定ありの場合はGETパラメータに追加する)
        url = f"{self.robobike_base_url}{ROBOBIKE_COMMAND_PREFIX}{button_index}"
        if value is not None:
            url += f"{ROBOBIKE_VALUE_SUFFIX}{value}"

        return url

    def send_command(self, button:str='only_data', value:float=None) -> dict:
        """
        Robobike 本番機にコマンドを送信します。

        Args:
            button (str): コマンド名(ROBOBIKE_COMMAND_NAMES に含まれるいずれかの要素)。デフォルトは 'only_data'。
            value (float, optional): ボタンに対応する値。指定しない場合は None。

        Returns:
            dict: 成功時はレスポンス情報、失敗時は 'status' と 'error' を含む辞書。
                数値フィールドの変換失敗時はエラーをログに記録し、解析を中止します。
                floatフィールドの非有限値（NaN・無限大）もエラーとして扱います。
                接続リセットや応答のデコード失敗もログに記録してエラー辞書を返します。
        """
        url = self._get_command_url(button, value)
        try:
            with urlopen(url, timeout=HTTP_TIMEOUT_SEC) as response:
                csv_str = response.read().decode('utf-8')
                #print(csv_str)
                # CSV をパースしてリストに変換
                csv_list = csv_str.strip().split(',')
                #print(csv_list)
                csv_dict = {}
                if len(csv_list) == ROBOBIKE_STATUS_CSV_INDEXES_LEN:
                    for i in range(ROBOBIKE_STATUS_CSV_INDEXES_LEN):
                        index = get_status_name(i)
                        try:
                            if index in ROBOBIKE_STATUS_CSV_INDEXES_FLOAT:
                                parsed_value = float(csv_list[i])
                                if not math.isfinite(parsed_value):
                                    raise ValueError(
                                        f'Non-finite numeric value: {csv_list[i]!r}'
                                    )
                            elif index in ROBOBIKE_STATUS_CSV_INDEXES_INT:
                                parsed_value = int(csv_list[i])
                            else:
                                parsed_value = csv_list[i]
                        except ValueError as error:
                            message = (
                                f'Invalid status value for {index}: '
                                f'{csv_list[i]!r} ({error})'
                            )
                            logger.exception(message)
                            return {'status': 'error', 'error': message}
                        csv_dict[index] = parsed_value
                    if csv_dict.get('OK', '').strip() != 'OK':
                        return {
                            'status': 'error',
                            'error': (
                                'Robobike reported command failure: '
                                f"OK={csv_dict.get('OK', '')!r}"
                            ),
                        }
                    return csv_dict
                else:
                    return {
                        'status': 'error',
                        'error': (
                            f'Unexpected response field count: {len(csv_list)} '
                                f'(expected {ROBOBIKE_STATUS_CSV_INDEXES_LEN})'
                        ),
                    }

        except (OSError, IncompleteRead, UnicodeDecodeError) as e:
            logger.exception('Failed to send Robobike command: %s', e)
            return {'status': 'error', 'error': str(e)}

    def get_status(self) -> dict[str, str | int | float] | None:
        """
        Robobikeのステータスを取得します。

        取得に成功した場合はステータス情報の辞書を返し、
        失敗した場合は status=error の辞書を返します。

        Returns:
            dict[str, str | int | float] | None: ステータス情報の辞書、
            通信失敗を含むエラーの場合は status=error の辞書
        """
        # command="only_data"の戻り値を返す 
        return self.send_command()

    def _get_telemetry_url(self) -> str:
        """
        Robobike テレメトリ取得用URL文字列を返します。

        Returns:
            str: Robobike テレメトリ取得用URL文字列
        """
        return f"{self.robobike_base_url}{ROBOBIKE_GET_ACC_PREFIX}"

    def _get_clear_buffer_url(self) -> str:
        """
        Robobike バッファクリア用URL文字列を返します。

        Returns:
            str: Robobike バッファクリア用URL文字列
        """
        return f"{self.robobike_base_url}{ROBOBIKE_CLEAR_BUFFER_PREFIX}"

    def get_telemetry(self) -> dict[str, str | int | float] | None:
        """取得をまたぐ履歴から、最新時刻を基準としたウィンドウ内の平均を返します。

        TELEMETRY_WINDOW_MSEC 以内のサンプルだけを保持します。
        time と a は最新行の値を維持し、時刻が戻った場合は履歴を破棄します。
        新規データがなければ履歴を再送せず None を返します。
        解析・デコードや通信に失敗した場合は status=error の辞書を返します。
        非有限値（NaN・無限大）や非有限の平均値もエラーとして扱います。
        ロボット側のバッファは自動消去しません。
        必要な場合は send_clear_buffer() を明示的に呼び出してください。
        """
        try:
            # /get_acc からCSV形式のテレメトリデータを取得
            with urlopen(self._get_telemetry_url(), timeout=HTTP_TIMEOUT_SEC * 60) as response:
                csv_str = response.read().decode('utf-8')

            # telemetryデータ格納用
            telemetry = []
            # CSVを1行ずつ解析し、各行を辞書としてtelemetryに追加
            for row_number, fields in enumerate(csv.reader(StringIO(csv_str)), start=1):
                # 空行や全て空白の行はスキップ
                if not fields or all(not field.strip() for field in fields):
                    continue
                # フィールド数が期待した項目数と異なる場合はエラー
                if len(fields) != ROBOBIKE_TELEMETRY_CSV_INDEXES_LEN:
                    raise ValueError(
                        f'Unexpected field count on row {row_number}: {len(fields)} '
                        f'(expected {ROBOBIKE_TELEMETRY_CSV_INDEXES_LEN})'
                    )

                # CSV1行を格納する変数
                sample: dict[str, str | int | float] = {}
                
                # インデックス配列＋CSV値配列をイテレータ化して1件づつ取り出す
                for index, raw_value in zip(ROBOBIKE_TELEMETRY_CSV_INDEXES, fields):
                    # 前後の空白を除去
                    raw_value = raw_value.strip()
                    try:
                        # インデックス対象がfloat値の場合
                        if index in ROBOBIKE_TELEMETRY_CSV_INDEXES_FLOAT:
                            value = float(raw_value)
                            if not math.isfinite(value):
                                raise ValueError(f'Non-finite numeric value: {raw_value!r}')
                        # インデックス対象がint値の場合
                        elif index in ROBOBIKE_TELEMETRY_CSV_INDEXES_INT:
                            value = int(raw_value)
                        # インデックス対象が文字列の場合はそのまま
                        else:
                            value = raw_value
                    # 変換エラーが発生した場合
                    except ValueError as error:
                        raise ValueError(
                            f'Invalid value for {index} on row {row_number}: {raw_value!r}'
                        ) from error
                    # 変換成功時はsampleに格納
                    sample[index] = value
                # sampleをtelemetryリストに追加
                telemetry.append(sample)

            # telemetryが空であればNoneを返す
            if not telemetry:
                return None

            # 最新のサンプルを取得
            latest_sample = max(telemetry, key=lambda sample: sample['time'])
            # 最新サンプルの時刻(int値)を取得
            latest_time = latest_sample['time']
            # int値でない場合はエラー
            if not isinstance(latest_time, int):
                raise ValueError(f'Invalid latest telemetry time: {latest_time!r}')

            # self._telemetry_historyが対象範囲外の場合は警告を出してクリア
            if (
                self._latest_telemetry_time is not None
                and latest_time < self._latest_telemetry_time
            ):
                logger.warning(
                    'Telemetry time moved backwards from %s to %s; discarding history',
                    self._latest_telemetry_time,
                    latest_time,
                )
                # ゼロ件リストにする
                self._telemetry_history.clear()
                self._latest_telemetry_time = None

            # 前回取得済みの時刻以前の行は捨てる(再送による重複防止)
            if self._latest_telemetry_time is not None:
                telemetry = [
                    sample for sample in telemetry
                    if (
                        isinstance(sample['time'], int)
                        and sample['time'] > self._latest_telemetry_time
                    )
                ]
                # 新規データがなければ履歴を再送せずNoneを返す
                if not telemetry:
                    return None

            # ウィンドウの開始時刻を計算
            window_start = latest_time - TELEMETRY_WINDOW_MSEC
            # ウィンドウ範囲内のsampleを抽出
            window_samples = [
                sample for sample in self._telemetry_history + telemetry
                if (
                    isinstance(sample['time'], int)
                    and window_start <= sample['time'] <= latest_time
                )
            ]

            # 平均sampleを格納する変数、初期値は最新サンプルで初期化
            averaged_sample = latest_sample.copy()
            # float値のインデックスについてウィンドウ内の平均を計算
            for index in ROBOBIKE_TELEMETRY_CSV_INDEXES_FLOAT:
                average = sum(
                    float(sample[index]) for sample in window_samples
                ) / len(window_samples)
                if not math.isfinite(average):
                    raise ValueError(f'Non-finite telemetry average for {index}')
                averaged_sample[index] = average
            # ここでintがないのは、実質time以外ないから

            # 履歴を更新（ウィンドウ内のサンプルのみを保持）
            self._telemetry_history = window_samples
            self._latest_telemetry_time = latest_time
            
            # averaged_sampleを返す
            return averaged_sample
        # 変換エラー、CSVエラーの場合
        except (ValueError, csv.Error) as error:
            logger.exception('Failed to parse Robobike telemetry: %s', error)
            # エラー情報の入った辞書を返す
            return {'status': 'error', 'error': str(error)}
        # 接続リセットを含む通信エラー、応答の途中切断の場合
        except (OSError, IncompleteRead) as e:
            logger.exception('Failed to retrieve Robobike telemetry: %s', e)
            # エラー情報の入った辞書を返す
            return {'status': 'error', 'error': str(e)}
    
    def send_clear_buffer(self) -> None:
        """
        ROBOBIKEに残っているテレメトリデータをクリアする。

        通信失敗（接続リセット・応答の途中切断を含む）と
        応答のデコード失敗はログに記録して再送出します。
        """
        try:
            # /clear_buffer を呼び出す
            with urlopen(self._get_clear_buffer_url(), timeout=HTTP_TIMEOUT_SEC) as response:
                # 戻り値を取得
                clear_result = response.read().decode('utf-8').strip()
                # 戻り値がOK以外であればエラー
                if clear_result != 'OK':
                    raise ValueError(f'Unexpected clear_buffer response: {clear_result!r}')
            return
        except (OSError, IncompleteRead, UnicodeDecodeError) as e:
            logger.exception('Failed to clear Robobike buffer: %s', e)
            raise


def test_robobike_bridge() -> None:
    # ダミーを使うかどうかを指定する引数を処理して、IPアドレスを決定する
    parser = argparse.ArgumentParser(
        prog="pub_robobike",
        description="Publish data from a WiFi-connected ROBOBIKE"
    )
    parser.add_argument(
        '--dummy',
        action='store_true',
        help='Use dummy data instead of real ROBOBIKE data')
    args = parser.parse_args()
    if args.dummy:
        default_ip = ROBOBIKE_DUMMY_IP
    else:
        default_ip = ROBOBIKE_DEFAULT_IP
    print(f'Using robobike IP: {default_ip}')

    # RobobikeBridgeインスタンスを作成
    bridge = RobobikeBridge(default_ip=default_ip)

    # only_data コマンドを送信
    print("Sending only_data command...")
    csv_dict = bridge.send_command()
    print(json.dumps(csv_dict, indent=4, ensure_ascii=False))

    # stp_all コマンドを送信
    print("Sending stp_all command...")
    csv_dict = bridge.send_command(button="stp_all")
    print(json.dumps(csv_dict, indent=4, ensure_ascii=False))

    # clear_buffer を送信
    print("Sending clear_buffer ...")
    bridge.send_clear_buffer()
    print("Clear buffer command sent.")

    # 1秒待機
    time.sleep(1)

    # テレメトリデータを取得
    print("Sending only_data command after clearing buffer...")
    csv_dict = bridge.get_telemetry()
    print(json.dumps(csv_dict, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    test_robobike_bridge()
