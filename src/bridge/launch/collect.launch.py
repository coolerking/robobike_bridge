"""
ファイル名: collect.launch.py

学習データ収集に必要なノードをまとめて起動します(Raspberry Pi 上で実行)。

    - pub_image       : 俯瞰カメラ画像の配信
    - pub_status      : ROBOBIKE ステータスの配信
    - pub_telemetry   : ROBOBIKE テレメトリの配信
    - pub_command_pad : ゲームパッド操作(START/BACK でエピソード開始/終了)
    - sub_command     : ROBOBIKE へのコマンド送信(watchdog:=true で方策ハートビートを監視)
    - record_session  : ros2 bag で ~/robobike_data/raw/<日時>/ に記録(record:=false で無効)
    - dummybike       : ダミーROBOBIKE(dummy:=true の場合のみ)

pub_image/pub_status/pub_telemetry はログが多いため画面には出さず ~/.ros/log に出力します。

実行例:
    ros2 launch bridge collect.launch.py                     # 実機で記録
    ros2 launch bridge collect.launch.py dummy:=true         # dummybike で記録(実機不要)
    ros2 launch bridge collect.launch.py dummy_camera:=true  # カメラなし(ダミー画像)
    ros2 launch bridge collect.launch.py record:=false       # 記録せずに操作のみ
    ros2 launch bridge collect.launch.py watchdog:=true      # 方策で走行(PC で pub_command_policy を実行)
"""
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PACKAGE = 'bridge'


def _is_true(context: LaunchContext, name: str) -> bool:
    """launch 引数の値を bool として返します。"""
    return LaunchConfiguration(name).perform(context).lower() in ('true', '1', 'yes')


def _create_nodes(context: LaunchContext) -> list:
    """launch 引数に応じてノードを作成します。"""
    dummy_args = ['--dummy'] if _is_true(context, 'dummy') else []
    dummy_camera_args = ['--dummy'] if _is_true(context, 'dummy_camera') else []
    watchdog_args = ['--watchdog'] if _is_true(context, 'watchdog') else []
    return [
        Node(package=PACKAGE, executable='pub_image', arguments=dummy_camera_args, output='log'),
        Node(package=PACKAGE, executable='pub_status', arguments=dummy_args, output='log'),
        Node(package=PACKAGE, executable='pub_telemetry', arguments=dummy_args, output='log'),
        Node(package=PACKAGE, executable='sub_command', arguments=dummy_args + watchdog_args,
             output='screen'),
        Node(package=PACKAGE, executable='pub_command_pad', output='screen'),
    ]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('dummy', default_value='false',
                              description='Use dummybike instead of the real ROBOBIKE'),
        DeclareLaunchArgument('dummy_camera', default_value='false',
                              description='Use dummy camera images'),
        DeclareLaunchArgument('record', default_value='true',
                              description='Record topics with ros2 bag (record_session)'),
        DeclareLaunchArgument('watchdog', default_value='false',
                              description='Stop the bike when the policy heartbeat is lost '
                                          '(use when running pub_command_policy on the PC)'),
        ExecuteProcess(
            cmd=['ros2', 'run', PACKAGE, 'dummybike'],
            output='log',
            condition=IfCondition(LaunchConfiguration('dummy')),
        ),
        OpaqueFunction(function=_create_nodes),
        ExecuteProcess(
            cmd=['ros2', 'run', PACKAGE, 'record_session'],
            output='screen',
            condition=IfCondition(LaunchConfiguration('record')),
        ),
    ])
