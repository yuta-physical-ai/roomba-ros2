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

## ディレクトリ

```
scripts/roomba_check.py      OI 接続確認スクリプト
scripts/encoder_check.py     エンコーダ確認スクリプト
udev/99-roomba.rules         /dev/roomba を作る udev ルール
roomba_bringup/              ROS2 パッケージ（launch・設定）
```

## ライセンス

MIT
