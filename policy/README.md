# policy: 学習データ変換・学習・推論ユーティリティ(PC専用)

LeRobot ACT で操舵方策を学習するための PC 側のスクリプトです。
ROS2 パッケージではないため `COLCON_IGNORE` を置いています(Raspberry Pi には不要)。

方策の入出力(状態・行動の項目や正規化)は `src/bridge/bridge/policy_features.py` で定義しています。

| 特徴量 | 内容 |
|---|---|
| `observation.images.overhead` | 俯瞰カメラ画像 320x240 RGB |
| `observation.state` | テレメトリ10項目(drv, str, std, sv_pos, gy_*, acc_*)＋ステータス mot_spd |
| `action` | steer(bt_Str_S の value / 100)、mot_spd(推論時は未使用) |

## Python 環境(リポジトリのトップに2つ)

| venv | Python | 用途 |
|---|---|---|
| `.venv` | 3.14(システム、ROS2 Lyrical と同じ) | bag の変換、推論(rclpy・rosbag2_py を使う) |
| `.venv-train` | 3.12(uv で作成) | 学習(`lerobot-train`) |

`lerobot-train` や `ACTPolicy.from_pretrained()` が使う draccus は Python 3.14 に未対応のため、
学習は 3.12 で行い、3.14 側でのモデル読み込みは `bridge/act_loader.py` を使います。

```bash
# .venv(ROS2 のパッケージを参照するため --system-site-packages)
source /opt/ros/lyrical/setup.bash
uv venv --system-site-packages --python /usr/bin/python3 .venv && touch .venv/COLCON_IGNORE
VIRTUAL_ENV=.venv uv pip install 'lerobot[dataset]==0.6.1' colcon-common-extensions

# .venv-train
uv venv --python 3.12 .venv-train && touch .venv-train/COLCON_IGNORE
VIRTUAL_ENV=.venv-train uv pip install 'lerobot[dataset,training]==0.6.1'
```

## 手順

### 1. 記録(Raspberry Pi)

必要なノードと記録(record_session)を一括起動します。`~/robobike_data/raw/<日時>/` に記録され、Ctrl+C で終了します。

```bash
ros2 launch bridge collect.launch.py                # 実機
ros2 launch bridge collect.launch.py dummy:=true    # dummybike(実機不要)
```

ゲームパッドの START でエピソード開始、BACK(または LB・切断)でエピソード終了です。
RB/LB はエピソードを記録せずに操作したいとき(スタート位置に戻すなど)に使います。

### 2. PC へコピー

```bash
rsync -av hori@10.0.0.8:robobike_data/raw/ ~/robobike_data/raw/
```

### 3. LeRobotDataset へ変換(.venv)

```bash
source /opt/ros/lyrical/setup.bash && source install/setup.bash
.venv/bin/python policy/convert_bag.py ~/robobike_data/raw/<日時> --list           # エピソード一覧
.venv/bin/python policy/convert_bag.py ~/robobike_data/raw/<日時> ... --name <データセット名> --exclude 2,5
```

`~/robobike_data/datasets/<データセット名>/` に保存されます。

### 4. 学習(.venv-train)

```bash
.venv-train/bin/lerobot-train \
  --dataset.repo_id=local/<データセット名> --dataset.root=$HOME/robobike_data/datasets/<データセット名> \
  --policy.type=act --policy.push_to_hub=false --policy.device=cuda \
  --wandb.enable=false --output_dir=$HOME/robobike_data/runs/<実行名>
```

### 5. 方策で走行(Raspberry Pi ＋ PC の .venv)

Raspberry Pi でウォッチドッグ付きで起動します(記録もされるので評価に使えます)。

```bash
ros2 launch bridge collect.launch.py watchdog:=true
```

PC で推論ノードを起動します(colcon でビルドした bridge を .venv の Python で実行)。

```bash
source /opt/ros/lyrical/setup.bash && source install/setup.bash
.venv/bin/python -m bridge.pub_command_policy \
  --model ~/robobike_data/runs/<実行名>/checkpoints/last/pretrained_model
```

- ゲームパッドの START で方策の操舵を開始、BACK/LB で停止します。速度はスティック上下で人が操作します
- 操舵中に画像・テレメトリ・ステータスが 0.5 秒途絶えると操舵を停止し、ウォッチドッグが緊急停止します
  (再開は START)
- `--n_action_steps` で1回の推論で実行するステップ数を変えられます(デフォルト 10 = 1秒分)
- `--autostart` で START を待たずに操舵を開始します(ゲームパッドなしのテスト用)

モデルの読み込みは `bridge.act_loader.load_act_policy()` で行います(draccus を使わないため 3.14 で動く)。
