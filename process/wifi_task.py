import subprocess, sys
import time
import os
from data.globalData import GDat, GObject, GObj
from debug.debugOut import log


# 读取 shell 环境变量
def read_shell_env():
    """
    优先从 gnome-shell 进程读取环境变量
    如果失败，则从当前环境读取
    如果当前环境也缺少必要变量，尝试自动设置默认值
    """
    try:
        # 尝试从 gnome-shell 进程读取
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
        # 从当前环境读取
        log.warning("未找到 gnome-shell 进程，从当前环境读取变量")
        result = {k: os.environ.get(k, "") for k in GDat.NEEDED}

        # 自动设置缺失的环境变量（使用合理的默认值）
        if not result.get("DISPLAY"):
            result["DISPLAY"] = ":0"
            log.warning(f"DISPLAY 未设置，使用默认值: :0")

        if not result.get("XDG_RUNTIME_DIR"):
            uid = os.getuid()
            result["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
            log.warning(f"XDG_RUNTIME_DIR 未设置，使用默认值: /run/user/{uid}")

        if not result.get("DBUS_SESSION_BUS_ADDRESS"):
            uid = os.getuid()
            result["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
            log.warning(f"DBUS_SESSION_BUS_ADDRESS 未设置，使用默认值: unix:path=/run/user/{uid}/bus")

        # WAYLAND_DISPLAY 是可选的，不需要检查
        # 在 X11 环境下可能不存在

        # 验证关键环境变量是否存在
        critical_vars = ["DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"]
        missing = [k for k in critical_vars if not result.get(k)]

        if missing:
            log.error(f"关键环境变量仍然缺失: {', '.join(missing)}")
            log.error("请检查系统环境或在 CLion Run Configuration 中设置环境变量")
            sys.exit(3)

        log.info("环境变量设置成功（使用当前环境 + 默认值）")

        # 打印最终使用的环境变量
        log.debug("最终环境变量:")
        for k, v in result.items():
            if k in critical_vars:  # 只打印关键变量
                log.debug(f"  {k} = {v}")

        return result

    except Exception as e:
        log.error(f"读取环境变量时发生错误: {e}")
        sys.exit(3)


# 启动浏览器
# 启动浏览器
def start_browser():
    shell_env = read_shell_env()

    # 打印将要使用的环境变量（用于调试）
    log.debug("使用的环境变量:")
    for k, v in shell_env.items():
        log.debug(f"  {k} = {v}")

    # 方案 1: 直接启动浏览器（推荐）
    # 合并当前环境变量和必需的桌面环境变量
    env = os.environ.copy()
    env.update(shell_env)

    cmd = [
        "/usr/bin/firefox", "--kiosk", GDat.reCamera  # 全屏
        # "/usr/bin/firefox", GDat.reCamera   # 普通模式
    ]

    log.info(f"启动浏览器命令: {' '.join(cmd)}")

    try:
        # 使用 subprocess.Popen 在后台启动
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # 在新会话中启动，避免被父进程影响
        )
        log.info(f"浏览器已启动，PID: {process.pid}")

        # 等待一小会，检查进程是否立即退出（说明启动失败）
        time.sleep(2)
        if process.poll() is not None:
            log.error(f"浏览器启动后立即退出，返回码: {process.returncode}")
            sys.exit(2)
        else:
            log.info("浏览器启动成功并正在运行")

    except Exception as e:
        log.error(f"启动浏览器时发生异常: {e}")
        log.error("请确保:")
        log.error("1. 已登录到图形桌面")
        log.error("2. Firefox 已安装")
        log.error("3. 环境变量设置正确")
        sys.exit(2)