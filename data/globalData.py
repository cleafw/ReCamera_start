class GObject:
    """
    GObject类
    """

    def __init__(self):
        pass


class GData:
    """
    GData类
    """

    def __init__(self):
        self.reCamera = "http://192.168.42.1/#/dashboard"  # reCamera 控制台 URL
        self.reCameraHost = "192.168.42.1"  # reCamera USB-NCM IP，用于开机等待检测
        self.usbIface = "usb0"  # reCamera 对应的 USB 网卡接口名
        self.waitTimeoutSec = 120  # 等待设备就绪的最长时间（秒）
        self.pollIntervalSec = 2  # 轮询间隔（秒）

        # 必需的桌面环境变量
        # WAYLAND_DISPLAY 改为可选，因为 X11 环境下不存在
        self.NEEDED = [
            "DISPLAY",              # X11 显示服务器（必需）
            "XDG_RUNTIME_DIR",      # 用户运行时目录（必需）
            "DBUS_SESSION_BUS_ADDRESS",  # D-Bus 会话总线（必需）
            "WAYLAND_DISPLAY",      # Wayland 显示（可选，X11 下不存在）
        ]


GObj = GObject()  # 全局对象
GDat = GData()  # 全局数据