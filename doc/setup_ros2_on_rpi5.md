# Ubuntu Desktop 26.04 LTS/Raspberry Pi 5(16GB) に ROS2 (Lyrical Luth) をインストールする方法

Dockerなどのコンテナを使わずに、Raspberry Pi 5のホストOS上に直接ROS2をインストールする場合、はRaspberry Pi OSではなくROS2対応のはやいUbuntuを選択するほうがいい。
またGazeboなどのGUIツールの確認を行いたい場合は Ubuntu ServerではなくUbuntu Desktopを選択しておきたい。

ということで執筆(2026/10/19)時点のRaspberry Pi 5 で動作する最新Ubuntu Desktopのうち最新版とそのOSに対応できるROSのバージョンは、以下の組となる。

- Ununtu Desktop 26.04.1 LTS
- ROS2 Lyrical Luth (2026/5 リリース)

よってこのバージョンを前提にインストール手順の概要を紹介する

## Raspberry Pi 5 に Ubuntu Desktop 26.04.1 LTS をインストールする

- PCにRaspberry Pi Imagerをインストール
- SDカードを指し Raspberry Pi Imagerを起動
- 以下の設定を行いWRITEする
    - Raspberry Pi 5 を選択
    - Other OS > Ubuntu Desktop 26.04.1 LTS (64bit)を選択
    - SDカードを選択
- SDカードを取り出す
- Raspberry Pi 5 にモニタ、キーボード、マウスを接続する
- 有線接続の場合、LANケーブルをつなぐ
- Raspberry Pi 5 にSDカードをさし、ACアダプタを接続して起動
- Ubuntu OSが起動
    - ユーザ・パスワード設定が必要なので設定する
    - WiFi接続の場合、Desktop画面右上からWiFi AP指定を行い接続する

## Ubuntu Desktop 上でROS2 Lyrical Luth をインストールする

- ターミナルを起動して、以下を実行する
```bash
sudo apt update && sudo apt upgrade -y && sudo apt install -y curl git locales software-properties-common
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install python3-colcon-common-extensions build-essential -y
sudo apt install python3-rosdep -y
sudo rosdep init
rosdep update
sudo apt update
sudo apt install python3-opencv -y
sudo apt install ros-dev-tools -y
sudo apt install build-essential cmake python3-rosdep python3-vcstool python3-pip -y
sudo apt install ros-lyrical-rqt ros-lyrical-rqt-common-plugins -y
sudo apt install ros-lyrical-ros2pkg ros-lyrical-ros2cli ros-lyrical-ros2run -y
echo "source /opt/ros/lyrical/setup.bash" >> ~/.bashrc
source ~/.bashrc
sudo apt autoremove -y
```

- Firefoxを起動し、以下の2つを実行する
    - [https://www.google.com](https://www.google.com) にアクセスしてログイン
    - [https://github.com](https://github.com) にアクセスしてログイン

- ターミナルに戻り、以下の操作を継続

```shell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
gh auth login #　ブラウザを使いながら認証を通す
```

## 本リポジトリの展開

- Raspberry Pi 5にUSBカメラが接続されていることを確認
- Raspberry Pi5デスクトップへログイン
- ターミナルを開き、以下のコマンドを実行する

```shell
cd
mkdir ros_ws
cd ros_ws
git clone https://github.com/coolerking/robobike_bridge.git
cd robobike_bridge
colcon build --symlink-install
source install/setup.bash
cd src/bridge/bridge
python3 pub_camera.py
```

> ずっとカメラ画像データを配信し続ける

- 別のターミナルを開き、以下のコマンドを実行する

```shell
cd ~/ros_ws/robobike_bridge/src/bridge/bridge
python3 sub_camera.py
```

カメラ画像が表示されたらOK

- 停止する場合は、両ターミナルでCtrl+Cを押す


<p align="right">以上</p>
