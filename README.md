# reCamera Kiosk 启动脚本说明

这个项目的作用很简单：  
在设备启动后，自动用浏览器全屏打开指定的 reCamera 控制台页面（Kiosk 模式）。

**在不同环境中使用时，主要改 `data/globalData.py` 里的配置：**
- reCamera 控制台地址（`reCamera`）
- reCamera 设备 IP（`reCameraHost`，用于开机等待检测）
- USB 网卡接口名（`usbIface`，reComputer 上一般为 `usb0`）

---

## 项目结构

```
ReCamera_start/
├── reCameraStart.py          # 主入口脚本
├── process/
│   └── wifi_task.py          # 等待设备就绪 + 浏览器启动逻辑
├── data/
│   ├── globalData.py         # 全局配置（地址、等待参数等）
│   └── path.py               # 日志路径配置
├── debug/
│   └── debugOut.py           # 日志输出模块
├── deploy/
│   ├── deploy_to_device.py   # 一键部署（支持多设备、指定 IP）
│   ├── devices.example.json  # 设备配置模板
│   ├── devices.local.json    # 本地设备配置（含密码，不入库）
│   ├── reCameraStart.desktop # 参考模板（部署时按设备路径自动生成）
│   └── reCamera.desktop
└── README.md                 # 本说明文件
```

---

## 1. 配置所在位置

打开 `data/globalData.py`，可以看到类似这样的代码：

```python
class GData:
    def __init__(self):
        self.reCamera = "http://192.168.42.1/#/dashboard"
        self.reCameraHost = "192.168.42.1"
        self.usbIface = "usb0"
        self.waitTimeoutSec = 120
        self.pollIntervalSec = 2

        self.NEEDED = [
            "DISPLAY",
            "XDG_RUNTIME_DIR",
            "DBUS_SESSION_BUS_ADDRESS",
            "WAYLAND_DISPLAY",
        ]
```

---

## 2. reCamera 地址与等待参数（按需修改）

### 控制台地址

字段：
```python
self.reCamera = "http://192.168.42.1/#/dashboard"
```

根据 reCamera 实际 IP 修改，例如：

```python
self.reCamera = "http://192.168.42.1/#/dashboard"
self.reCameraHost = "192.168.42.1"
```

如果 IP 变了（例如 `192.168.1.100`），**两个字段要一起改**：

```python
self.reCamera = "http://192.168.1.100/#/dashboard"
self.reCameraHost = "192.168.1.100"
```

### 开机等待参数

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `usbIface` | `usb0` | reCamera USB-NCM 网卡名，可用 `ip addr` 查看 |
| `waitTimeoutSec` | `120` | 最长等待时间（秒） |
| `pollIntervalSec` | `2` | 每次检测间隔（秒） |

开机时脚本会依次等待：

1. `gnome-shell` 桌面就绪  
2. `usbIface` 网卡获取 IP  
3. `http://reCameraHost/` 返回正常响应  

全部就绪后再启动 Firefox，避免重启后页面显示「无法连接」。

---

## 3. NEEDED：桌面环境变量（一般不用改）

```python
self.NEEDED = [
    "DISPLAY",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "WAYLAND_DISPLAY",
]
```

脚本会自动从 `gnome-shell` 进程读取这些变量；读取失败时使用合理默认值。

---

## 4. 安装与运行

### 4.1 依赖安装

```bash
python3 -m venv ~/Seeed/venv
source ~/Seeed/venv/bin/activate
pip install colorlog
```

### 4.2 手动运行测试

```bash
cd /home/seeed/Seeed/ReCamera_start
source /home/seeed/Seeed/venv/bin/activate
python3 reCameraStart.py
```

如果一切正常，Firefox 会以 Kiosk 模式全屏打开 reCamera 控制台。

---

## 5. 开机自启动配置

### 方案一：使用 autostart 桌面文件（推荐）

将 `deploy/reCameraStart.desktop` 复制到自启动目录，并按实际路径修改 `Exec` 中的 venv 与脚本路径：

```bash
mkdir -p ~/.config/autostart
cp deploy/reCameraStart.desktop ~/.config/autostart/
chmod 644 ~/.config/autostart/reCameraStart.desktop
```

桌面快捷方式（手动点击启动）：

```bash
cp deploy/reCamera.desktop ~/Desktop/
chmod +x ~/Desktop/reCamera.desktop
```

`reCameraStart.desktop` 中建议保留：

```ini
X-GNOME-Autostart-Delay=5
```

作为额外缓冲；主要等待逻辑由 `wifi_task.py` 内的轮询完成，不再依赖固定 `sleep`。

### 方案二：使用 systemd 用户服务

若使用 systemd，请在 `ExecStart` 中调用本项目的 `reCameraStart.py`，**不要**直接启动 Firefox（会跳过等待逻辑）：

```ini
[Service]
Type=simple
ExecStart=/home/seeed/Seeed/venv/bin/python /home/seeed/Seeed/ReCamera_start/reCameraStart.py
Environment="DISPLAY=:0"
```

---

## 6. 浏览器模式切换

在 `process/wifi_task.py` 的 `start_browser()` 中：

```python
cmd = [
    "/usr/bin/firefox", "--kiosk", GDat.reCamera  # 全屏 Kiosk 模式
    # "/usr/bin/firefox", GDat.reCamera           # 普通窗口模式
]
```

---

## 7. 日志查看

日志文件保存在 `data/logs/` 目录下：

```bash
ls data/logs/
cat data/logs/$(date +%Y-%m-%d)-all.log
```

---

## 8. 故障排查

### 问题：重启后页面显示「无法连接」，手动点桌面图标又正常

**原因：** 开机自启动时 Firefox 打开过早，reCamera 的 USB 网卡（`usb0`）尚未就绪。

**处理：** 使用当前版本脚本即可（已内置等待逻辑）。若仍偶发失败，可增大 `waitTimeoutSec`，或检查 USB 线连接。

验证网卡与连通性：

```bash
ip addr show usb0
ping -c 2 192.168.42.1
curl -I --connect-timeout 3 http://192.168.42.1/
```

### 问题：手动运行正常，但开机不自启动

1. 检查自动登录是否开启（`/etc/gdm3/custom.conf`）
2. 确认 `~/.config/autostart/reCameraStart.desktop` 存在且 `X-GNOME-Autostart-enabled=true`
3. desktop 文件权限应为 `644`（不要带可执行位）

### 问题：浏览器启动失败

```bash
which firefox
echo $DISPLAY
```

并查看 `data/logs/` 下当日日志。

### 问题：页面打不开

1. 确认 reCamera 已通过 USB 连接（`lsusb` 中应有 Cvitek NCM）
2. 确认 `reCamera` 与 `reCameraHost` 配置一致
3. 在普通浏览器中手动访问地址测试

---

## 9. 一键部署到不同设备

IP 会变、设备有多台时，**不要写死 IP**。使用 `deploy/devices.local.json` 管理设备列表。

### 9.1 首次配置

```bash
# 复制模板
cp deploy/devices.example.json deploy/devices.local.json
```

编辑 `deploy/devices.local.json`，为每台 recomputer 添加一条记录：

```json
{
  "default": "recomputer-office",
  "devices": {
    "recomputer-office": {
      "host": "192.168.1.28",
      "user": "seeed",
      "password": "你的密码",
      "remote_home": "/home/seeed",
      "project_dir": "Seeed/ReCamera_start",
      "venv_dir": "Seeed/venv"
    },
    "recomputer-home": {
      "host": "192.168.2.50",
      "user": "seeed",
      "password": "你的密码",
      "remote_home": "/home/seeed",
      "project_dir": "Seeed/ReCamera_start",
      "venv_dir": "Seeed/venv"
    }
  }
}
```

`devices.local.json` 已加入 `.gitignore`，密码不会误提交。

### 9.2 部署命令

安装部署依赖（仅在你自己的电脑上执行一次）：

```bash
pip install paramiko
```

常用命令：

```bash
# 查看已配置设备
python deploy/deploy_to_device.py --list

# 部署到默认设备
python deploy/deploy_to_device.py

# 部署到指定名称的设备
python deploy/deploy_to_device.py --device recomputer-home

# IP 临时变了：只覆盖 host，其他仍用配置里的账号密码
python deploy/deploy_to_device.py --device recomputer-office --host 192.168.1.99

# 先看会传什么，不实际上传
python deploy/deploy_to_device.py --device recomputer-office --dry-run
```

也可用环境变量（适合 CI 或不想在命令行写密码）：

```bash
set RECAMERA_DEPLOY_DEVICE=recomputer-office
set RECAMERA_DEPLOY_HOST=192.168.1.99
set RECAMERA_DEPLOY_PASSWORD=你的密码
python deploy/deploy_to_device.py
```

### 9.3 部署前会做什么

1. **TCP 连通性检查** — 确认 IP 和 SSH 端口可达  
2. **SSH 登录** — 验证用户名密码  
3. **上传代码** — `reCameraStart.py`、`process/`、`data/`、`debug/`  
4. **生成 desktop 文件** — 按该设备的 `remote_home`、`venv_dir` 自动写入路径  
5. **远程语法检查** — `py_compile` 确保脚本无语法错误  

部署失败时会明确提示是「连不上」还是「密码错」，不会静默部署到错误设备。

---

## 10. 修改步骤总结

1. 打开 `data/globalData.py`，修改 `reCamera`、`reCameraHost` 等
2. 在 `deploy/devices.local.json` 中维护各设备的 SSH 地址
3. 执行 `python deploy/deploy_to_device.py --device 设备名`（IP 变了加 `--host`）
4. 重启目标设备验证
