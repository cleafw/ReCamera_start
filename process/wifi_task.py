import subprocess
import sys
import time
import os
import urllib.request
import urllib.error

from data.globalData import GDat
from debug.debugOut import log


def read_shell_env():
    """
    优先从 gnome-shell 进程读取环境变量
    如果失败，则从当前环境读取
    如果当前环境也缺少必要变量，尝试自动设置默认值
    """
    try:
        pid = subprocess.check_output(["pgrep", "-n", "gnome-shell"]).decode().strip()
        log.info(f"找到 gnome-shell 进程 PID: {pid}")

        env = {}
        with open(f"/proc/{pid}/environ", "rb") as f:
            for kv in f.read().split(b"\x00"):
                if b"=" in kv:
                    k, v = kv.split(b"=", 1)
                    env[k.decode()] = v.decode()

        result = {k: env.get(k, "") for k in GDat.NEEDED}
        log.info("从 gnome-shell 进程读取环境变量成功")
        return result

    except subprocess.CalledProcessError:
        log.warning("未找到 gnome-shell 进程，从当前环境读取变量")
        result = {k: os.environ.get(k, "") for k in GDat.NEEDED}

        if not result.get("DISPLAY"):
            result["DISPLAY"] = ":0"
            log.warning("DISPLAY 未设置，使用默认值: :0")

        if not result.get("XDG_RUNTIME_DIR"):
            uid = os.getuid()
            result["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
            log.warning(f"XDG_RUNTIME_DIR 未设置，使用默认值: /run/user/{uid}")

        if not result.get("DBUS_SESSION_BUS_ADDRESS"):
            uid = os.getuid()
            result["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
            log.warning(
                f"DBUS_SESSION_BUS_ADDRESS 未设置，使用默认值: unix:path=/run/user/{uid}/bus"
            )

        critical_vars = ["DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"]
        missing = [k for k in critical_vars if not result.get(k)]

        if missing:
            log.error(f"关键环境变量仍然缺失: {', '.join(missing)}")
            log.error("请检查系统环境或在 CLion Run Configuration 中设置环境变量")
            sys.exit(3)

        log.info("环境变量设置成功（使用当前环境 + 默认值）")
        log.debug("最终环境变量:")
        for k, v in result.items():
            if k in critical_vars:
                log.debug(f"  {k} = {v}")

        return result

    except Exception as e:
        log.error(f"读取环境变量时发生错误: {e}")
        sys.exit(3)


def wait_for_gnome_shell(timeout_sec: int = 60) -> bool:
    """开机自启时桌面可能尚未就绪，等待 gnome-shell 出现。"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            subprocess.check_output(["pgrep", "-x", "gnome-shell"], stderr=subprocess.DEVNULL)
            log.info("gnome-shell 已就绪")
            return True
        except subprocess.CalledProcessError:
            log.info("等待 gnome-shell 启动...")
            time.sleep(GDat.pollIntervalSec)
    log.warning("等待 gnome-shell 超时，继续执行")
    return False


def usb_iface_has_ipv4(iface: str) -> bool:
    try:
        out = subprocess.check_output(
            ["ip", "-4", "addr", "show", iface],
            stderr=subprocess.DEVNULL,
        ).decode()
        return "inet " in out
    except subprocess.CalledProcessError:
        return False


def wait_for_usb_network(timeout_sec: int | None = None) -> bool:
    """等待 reCamera USB-NCM 网卡就绪并获取 IP。"""
    timeout_sec = timeout_sec if timeout_sec is not None else GDat.waitTimeoutSec
    iface = GDat.usbIface
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if usb_iface_has_ipv4(iface):
            log.info(f"{iface} 网卡已获取 IP，USB 网络就绪")
            return True
        log.info(f"等待 {iface} USB 网卡就绪...")
        time.sleep(GDat.pollIntervalSec)
    log.error(f"等待 {iface} 超时（{timeout_sec}s）")
    return False


def recamera_http_ready(host: str | None = None, timeout_sec: float = 3.0) -> bool:
    host = host or GDat.reCameraHost
    url = f"http://{host}/"
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            return resp.status < 500
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.info(f"reCamera 尚未就绪 ({host}): {exc}")
        return False


def wait_for_recamera(timeout_sec: int | None = None) -> bool:
    """等待 reCamera Web 服务可访问。"""
    timeout_sec = timeout_sec if timeout_sec is not None else GDat.waitTimeoutSec
    host = GDat.reCameraHost
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if recamera_http_ready(host):
            log.info(f"reCamera HTTP 服务已就绪: http://{host}/")
            return True
        time.sleep(GDat.pollIntervalSec)
    log.error(f"等待 reCamera HTTP 超时（{timeout_sec}s）")
    return False


def wait_for_recamera_ready() -> None:
    """
    开机自启时 USB 网卡与 reCamera 往往晚于浏览器脚本。
    必须先等待网络和 HTTP 服务就绪，再打开 Firefox。
    """
    log.info("等待 reCamera 设备与网络就绪...")
    wait_for_gnome_shell()
    wait_for_usb_network()
    if not wait_for_recamera():
        log.warning("reCamera 仍未响应，将尝试打开浏览器（页面可能暂时无法连接）")


def start_browser():
    wait_for_recamera_ready()

    shell_env = read_shell_env()

    log.debug("使用的环境变量:")
    for k, v in shell_env.items():
        log.debug(f"  {k} = {v}")

    env = os.environ.copy()
    env.update(shell_env)

    cmd = [
        "/usr/bin/firefox",
        "--kiosk",
        GDat.reCamera,
        # "/usr/bin/firefox", GDat.reCamera   # 普通模式
    ]

    log.info(f"启动浏览器命令: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log.info(f"浏览器已启动，PID: {process.pid}")

        time.sleep(2)
        if process.poll() is not None:
            log.error(f"浏览器启动后立即退出，返回码: {process.returncode}")
            sys.exit(2)
        log.info("浏览器启动成功并正在运行")

    except Exception as e:
        log.error(f"启动浏览器时发生异常: {e}")
        log.error("请确保:")
        log.error("1. 已登录到图形桌面")
        log.error("2. Firefox 已安装")
        log.error("3. 环境变量设置正确")
        sys.exit(2)
