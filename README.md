# roomba-ros2

Jetson Orin Nano + ROS2 Humble でルンバ600系を動かすための設定・ツール一式です。
ルンバの OI（Open Interface）に USB-TTL アダプタ経由でシリアル接続します。

## 構成

| 機器 | 接続 | デバイス名 |
| --- | --- | --- |
| ルンバ 600系 | USB-TTL アダプタ（CH9102, 5V TTL）→ ミニDIN 7ピン | `/dev/roomba` |
| YDLIDAR X4 Pro | USB | `/dev/lidar`（予定） |
| USBカメラ | USB | — |

## 配線

アダプタの TX/RX はルンバ側と交差させます。

| USB-TTL アダプタ | ルンバ ミニDIN 7ピン |
| --- | --- |
| TxD | 3 RXD |
| RxD | 4 TXD |
| GND | 6 / 7 GND |
| DTR または RTS（任意） | 5 BRC |
| +5V / VIO | 接続しない |
| — | 1 / 2 Vpwr：**接続しない** |

> [!WARNING]
> Vpwr（ピン1・2）にはバッテリー電圧（最大約21V）が出ています。アダプタや Jetson に繋ぐと壊れます。
> Jetson の GPIO UART（3.3V）にルンバの TX（5V）を直結しないでください。

通信速度は 115200bps です。

## セットアップ

### 1. シリアルポートの権限と固定名

```bash
sudo usermod -aG dialout $USER        # 反映には再ログインが必要
```

`udev/99-roomba.rules` はアダプタのシリアル番号で `/dev/roomba` を作ります。
別のアダプタを使う場合は `udevadm info -q property -n /dev/ttyACM0 | grep ID_SERIAL_SHORT` で番号を調べて書き換えてください。

```bash
sudo cp udev/99-roomba.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -l /dev/roomba
```

### 2. 接続確認

ルンバの電源を入れてから実行します。依存ライブラリは不要です（Python 標準ライブラリのみ）。

```bash
python3 scripts/roomba_check.py /dev/roomba          # バッテリー情報を読む
python3 scripts/roomba_check.py /dev/roomba --beep   # さらに2音鳴らす
```

成功すると電圧・電流・温度・残量が表示され、`RESULT: OK` が出ます。
受信が `0/10 bytes` のときは TX/RX の交差と GND、ルンバが起動しているかを確認してください。
ルンバはしばらく操作がないとスリープするので、その場合は CLEAN ボタンで起こします。

### 3. エンコーダ確認

```bash
python3 scripts/encoder_check.py /dev/roomba               # 15秒間、手で車輪を回して確認
python3 scripts/encoder_check.py /dev/roomba --drive --mm 30  # 実際に30mm前進して左右を比較
```

`--drive` は Safe モードで走るので、床に置き、指定距離の2倍以上前方を空けてください。

### 4. ROS2 で起動

ドライバには [create_robot](https://github.com/AutonomyLab/create_robot) を使います。
`create_robot` を同じワークスペースに入れてからビルドします。

```bash
cd ~/ros2_ws/src
ln -s ~/roomba-ros2/roomba_bringup .
# create_robot と libcreate を src に clone しておく
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch roomba_bringup roomba.launch.py
```

パラメータは `roomba_bringup/config/roomba.yaml` にあります。

### 5. Gazebo でシミュレーション

Gazebo Fortress（`ign gazebo`）を使います。モデルの寸法とメッシュは `create_robot` の `create_description` を流用しています。
トピック名（`/cmd_vel`・`/odom`・`/tf`・`/joint_states`）は実機の `create_driver` と同じです。

```bash
cd ~/ros2_ws/src
ln -s ~/roomba-ros2/roomba_gazebo .
# create_robot（humble ブランチ）を src に clone しておく
cd ~/ros2_ws
colcon build --symlink-install --packages-select create_description roomba_gazebo
source install/setup.bash
ros2 launch roomba_gazebo sim.launch.py            # サーバーのみ（ヘッドレス）
ros2 launch roomba_gazebo sim.launch.py gui:=true  # GUI も起動
ros2 launch roomba_gazebo sim.launch.py rviz:=true # RViz も起動
```

| 引数 | デフォルト | 内容 |
| --- | --- | --- |
| `world` | `worlds/room.sdf` | 5×4 m の部屋（壁・ソファ・棚・脚付きローテーブル・ゴミ箱）。`worlds/empty.sdf` は床だけ |
| `odom_source` | `gazebo` | `/odom` と TF `odom→base_footprint` を誰が出すか（下記） |
| `joint_state_rate` | `50.0` | `/joint_states` の周期 [Hz]。実機の `create_driver` は `loop_hz`（10 Hz） |
| `rviz` | `false` | RViz を起動（`/scan`・真値・`/odom` の軌跡を表示） |
| `foxglove` | `true` | foxglove_bridge を起動（`ws://<Jetson>:8765`）。ブラウザの Foxglove で表示でき、描画はブラウザ側で行う |
| `gui` / `render_engine` | `false` / `ogre` | Gazebo GUI と描画エンジン |

主なトピック：

| トピック | 型 | 内容 |
| --- | --- | --- |
| `/cmd_vel` | Twist | 速度指令（実機と同じ） |
| `/joint_states` | JointState | 左右ホイール角 `left_wheel_joint`・`right_wheel_joint` [rad]（累積値） |
| `/scan` | LaserScan | YDLIDAR X4 Pro 相当（360°、720点、7 Hz、0.12–10 m、フレーム `laser_link`） |
| `/odom` | Odometry | オドメトリ（`odom_source` で切替） |
| `/ground_truth/odom` | Odometry | 物理エンジンの真値。オドメトリ誤差の評価用（シミュレーションのみ） |
| `/diff_drive/odom` | Odometry | DiffDrive プラグインの推定値（`odom_source:=user` のときだけ） |

#### 自作オドメトリノードで動かす

`odom_source:=user` にすると、Gazebo は `/odom` と TF `odom→base_footprint` を出さなくなります。
自分のノードで `/joint_states` からこれらを出してください。プラグインの推定値は `/diff_drive/odom` に、真値は `/ground_truth/odom` に出るので、RViz（緑：真値、橙：`/odom`、青：プラグイン）で比べられます。

エンコーダオドメトリのノードは `roomba_odometry` パッケージにあります（`roomba_odometry/wheel_odometry.py`）。

```bash
cd ~/ros2_ws/src
ln -s ~/roomba-ros2/roomba_odometry .
cd ~/ros2_ws
colcon build --symlink-install --packages-select roomba_odometry
source install/setup.bash
ros2 launch roomba_gazebo sim.launch.py odom_source:=user rviz:=true
ros2 launch roomba_odometry wheel_odometry.launch.py   # 別ターミナル。実機では use_sim_time:=false
```

計算に使う値は `urdf/roomba.urdf.xacro` にあります（実機 Create 2 OI の仕様値）。

- ホイール半径 `wheel_radius` = 0.036 m
- ホイール間距離 `wheel_separation` = 0.235 m

LiDAR の取り付け位置（`laser_x`・`laser_z`）は仮の値です。マウントを作ったら実測して書き換えてください。

別のターミナルで動かします。

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
ros2 topic echo /odom
```

> [!NOTE]
> Gazebo の DiffDrive は最後に受け取った `/cmd_vel` を保持し続けます。止めるときはゼロ速度を送ってください。
> `gz sim` コマンドは Garden（gz-sim 7）が起動するため、ros_gz と通信できません。launch を使ってください。
> Jetson Orin Nano では OGRE2 が GPU メモリ確保に失敗して落ちるため、描画エンジンはデフォルトで OGRE1（`render_engine:=ogre`）にしています。
> LiDAR の描画には X ディスプレイが必要です。SSH から起動して `DISPLAY` が無いときは、launch が Jetson のデスクトップ（`:0`）を使います。

## ディレクトリ

```
scripts/roomba_check.py      OI 接続確認スクリプト
scripts/encoder_check.py     エンコーダ確認スクリプト
udev/99-roomba.rules         /dev/roomba を作る udev ルール
roomba_bringup/              ROS2 パッケージ（launch・設定）
roomba_gazebo/               ROS2 パッケージ（Gazebo Fortress シミュレーション）
roomba_odometry/             ROS2 パッケージ（エンコーダオドメトリ）
```

## ライセンス

MIT
