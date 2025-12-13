# reCamera Kiosk 启动脚本说明

这个项目的作用很简单：  
在设备启动后，自动用浏览器全屏打开指定的 reCamera 控制台页面（Kiosk 模式）。

**在不同环境中使用时，主要只需要改 1 个地方：**
- 要访问的 **reCamera 地址**

这个配置在 `data/globalData.py` 里。

---

## 项目结构

```
reCameraStart/
├── reCameraStart.py          # 主入口脚本
├── process/
│   └── wifi_task.py          # 浏览器启动逻辑
├── data/
│   ├── globalData.py         # 全局配置（reCamera 地址等）
│   └── path.py               # 日志路径配置
├── debug/
│   └── debugOut.py           # 日志输出模块
└── README.md                 # 本说明文件
```

---

## 1. 配置所在位置

打开 `data/globalData.py`，可以看到类似这样的代码：

```python
class GData:
    def __init__(self):
        # reCamera 控制台地址
        self.reCamera = "http://192.168.42.1/#/dashboard"

        # 桌面环境变量（一般不用改）
        self.NEEDED = [
            "DISPLAY",
            "XDG_RUNTIME_DIR",
            "DBUS_SESSION_BUS_ADDRESS",
            "WAYLAND_DISPLAY",
        ]
```

---

## 2. reCamera：控制台地址（按需修改）

字段：
```python
self.reCamera = "http://192.168.42.1/#/dashboard"
```

根据你的 reCamera 设备实际 IP 地址来改：

- 如果 reCamera 的 IP 是 **192.168.42.1**（默认）：
  ```python
  self.reCamera = "http://192.168.42.1/#/dashboard"
  ```

- 如果 reCamera 的 IP 变了，比如 **192.168.1.100**：
  ```python
  self.reCamera = "http://192.168.1.100/#/dashboard"
  ```

- 如果想打开 **其他页面**：
  ```python
  self.reCamera = "http://192.168.42.1/#/settings"
  ```

> ✅ 换一台 reCamera 设备时：只要 IP 地址变了，就改 `self.reCamera` 为新的地址即可。

---

## 3. NEEDED：桌面环境变量（一般不用改）

字段：
```python
self.NEEDED = [
    "DISPLAY",              # X11 显示服务器（必需）
    "XDG_RUNTIME_DIR",      # 用户运行时目录（必需）
    "DBUS_SESSION_BUS_ADDRESS",  # D-Bus 会话总线（必需）
    "WAYLAND_DISPLAY",      # Wayland 显示（可选，X11 下不存在）
]
```

这是用于把桌面环境的一些变量传给浏览器的，一般保持默认即可：
- 不换桌面环境 / 显示服务器时，**不要改它**。
- 脚本会自动尝试从 `gnome-shell` 进程读取这些变量，如果读取失败会使用默认值。

---

## 4. 安装与运行

### 4.1 依赖安装

```bash
# 创建虚拟环境（可选）
python3 -m venv ~/myenv
source ~/myenv/bin/activate

# 安装依赖
pip install colorlog
```

### 4.2 手动运行测试

```bash
cd /home/recomputer/seeed/reCameraStart
python3 reCameraStart.py
```

如果一切正常，Firefox 浏览器会以 Kiosk 模式全屏打开 reCamera 控制台。

---

## 5. 开机自启动配置

### 方案一：使用 autostart 桌面文件（推荐）

这是最简单可靠的方式：

```bash
# 创建 autostart 目录
mkdir -p ~/.config/autostart

# 创建桌面启动文件
cat > ~/.config/autostart/recamera.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=reCamera Browser
Comment=Auto start reCamera dashboard
Exec=sh -c 'sleep 5 && /home/recomputer/myenv/bin/python /home/recomputer/seeed/reCameraStart/reCameraStart.py'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=false
EOF
```

重启后浏览器会自动打开。

### 方案二：使用 systemd 用户服务

```bash
# 创建服务目录
mkdir -p ~/.config/systemd/user/

# 创建服务文件
cat > ~/.config/systemd/user/recamera.service << 'EOF'
[Unit]
Description=reCamera Firefox Kiosk
After=default.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/firefox --kiosk http://192.168.42.1/#/dashboard
Restart=on-failure
RestartSec=5
Environment="DISPLAY=:0"

[Install]
WantedBy=default.target
EOF

# 启用 lingering（让用户服务开机就启动）
sudo loginctl enable-linger $USER

# 重新加载并启用服务
systemctl --user daemon-reload
systemctl --user enable recamera.service
systemctl --user start recamera.service
```

---

## 6. 浏览器模式切换

在 `process/wifi_task.py` 中可以切换浏览器启动模式：

```python
cmd = [
    "/usr/bin/firefox", "--kiosk", GDat.reCamera  # 全屏 Kiosk 模式
    # "/usr/bin/firefox", GDat.reCamera           # 普通窗口模式
]
```

- `--kiosk`：全屏模式，无地址栏、无菜单栏，适合展示用
- 不加参数：普通窗口模式，方便调试

---

## 7. 日志查看

日志文件保存在 `data/logs/` 目录下：

```bash
# 查看今天的日志
ls /home/recomputer/seeed/reCameraStart/data/logs/

# 查看日志内容
cat /home/recomputer/seeed/reCameraStart/data/logs/$(date +%Y-%m-%d)-all.log
```

---

## 8. 故障排查

### 问题：手动运行正常，但开机不自启动

1. 检查自动登录是否开启：
   ```bash
   sudo cat /etc/gdm3/custom.conf
   ```
   确保有：
   ```ini
   [daemon]
   AutomaticLoginEnable=true
   AutomaticLogin=recomputer
   ```

2. 如果用 systemd 服务，检查 lingering 是否开启：
   ```bash
   sudo loginctl enable-linger recomputer
   ```

### 问题：浏览器启动失败

1. 确认 Firefox 已安装：
   ```bash
   which firefox
   ```

2. 确认图形环境正常运行：
   ```bash
   echo $DISPLAY
   ```

3. 查看日志文件了解详细错误信息。

### 问题：页面打不开

1. 确认 reCamera 设备已连接
2. 测试网络连通性：
   ```bash
   ping 192.168.42.1
   ```
3. 在普通浏览器中手动访问地址测试

---

## 9. 修改步骤总结

1. 打开项目中的 `data/globalData.py`
2. 找到 `class GData` 里的 `__init__` 函数
3. 按你的环境修改：
   ```python
   self.reCamera = "你的 reCamera 地址"
   ```
4. 保存文件，重新运行启动脚本或重启设备

这样就完成了在不同环境下的基础适配。
