#!/usr/bin/env python3
"""Deploy ReCamera_start to one or more recomputer devices over SSH."""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

import paramiko

DEPLOY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEPLOY_DIR.parent

CODE_FILES = (
    "reCameraStart.py",
    "process/wifi_task.py",
    "data/globalData.py",
    "data/path.py",
    "debug/debugOut.py",
)


@dataclass
class DeviceTarget:
    name: str
    host: str
    port: int
    user: str
    password: str
    remote_home: str
    project_dir: str
    venv_dir: str

    @property
    def remote_root(self) -> str:
        return f"{self.remote_home.rstrip('/')}/{self.project_dir.strip('/')}"

    @property
    def remote_venv(self) -> str:
        return f"{self.remote_home.rstrip('/')}/{self.venv_dir.strip('/')}"

    @property
    def remote_autostart(self) -> str:
        return f"{self.remote_home.rstrip('/')}/.config/autostart/reCameraStart.desktop"

    @property
    def remote_desktop(self) -> str:
        return f"{self.remote_home.rstrip('/')}/Desktop/reCamera.desktop"


def load_config(config_path: Path) -> dict:
    if not config_path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with config_path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_config_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    local = DEPLOY_DIR / "devices.local.json"
    if local.is_file():
        return local
    return DEPLOY_DIR / "devices.example.json"


def build_target(
    config: dict,
    device_name: str | None,
    host: str | None,
    port: int | None,
    user: str | None,
    password: str | None,
    remote_home: str | None,
) -> DeviceTarget:
    devices = config.get("devices", {})
    if not devices:
        raise ValueError("配置文件中没有 devices 条目")

    name = device_name or os.environ.get("RECAMERA_DEPLOY_DEVICE") or config.get("default")
    if not name:
        raise ValueError("请用 --device 指定设备，或在配置中设置 default")

    if name not in devices:
        known = ", ".join(sorted(devices))
        raise ValueError(f"未知设备 '{name}'，可选: {known}")

    entry = dict(devices[name])
    entry.pop("comment", None)

    resolved_host = host or os.environ.get("RECAMERA_DEPLOY_HOST") or entry.get("host")
    if not resolved_host:
        raise ValueError(f"设备 '{name}' 未配置 host，请用 --host 指定")

    resolved_password = (
        password
        or os.environ.get("RECAMERA_DEPLOY_PASSWORD")
        or entry.get("password")
    )
    if not resolved_password or resolved_password == "CHANGE_ME":
        raise ValueError(
            f"设备 '{name}' 未配置有效密码。"
            "请在 devices.local.json 填写，或使用环境变量 RECAMERA_DEPLOY_PASSWORD / --password"
        )

    return DeviceTarget(
        name=name,
        host=resolved_host,
        port=port or int(os.environ.get("RECAMERA_DEPLOY_PORT", entry.get("port", 22))),
        user=user or os.environ.get("RECAMERA_DEPLOY_USER") or entry.get("user", "seeed"),
        password=resolved_password,
        remote_home=remote_home or entry.get("remote_home", "/home/seeed"),
        project_dir=entry.get("project_dir", "Seeed/ReCamera_start"),
        venv_dir=entry.get("venv_dir", "Seeed/venv"),
    )


def list_devices(config: dict) -> None:
    default = config.get("default", "")
    print("已配置设备:")
    for name, entry in sorted(config.get("devices", {}).items()):
        mark = " (default)" if name == default else ""
        host = entry.get("host", "?")
        user = entry.get("user", "?")
        comment = entry.get("comment", "")
        line = f"  - {name}: {user}@{host}{mark}"
        if comment:
            line += f"  # {comment}"
        print(line)
    print()
    print("用法示例:")
    print("  python deploy/deploy_to_device.py --device recomputer-office")
    print("  python deploy/deploy_to_device.py --host 192.168.1.50 --device recomputer-office")
    print("  python deploy/deploy_to_device.py --list")


def check_reachable(target: DeviceTarget, timeout: float = 3.0) -> None:
    print(f"检查连通性: {target.host}:{target.port} ...", end=" ")
    try:
        with socket.create_connection((target.host, target.port), timeout=timeout):
            print("OK")
    except OSError as exc:
        raise ConnectionError(
            f"无法连接 {target.host}:{target.port}，请确认 IP/网线/WiFi 是否正确。详情: {exc}"
        ) from exc


def render_autostart_desktop(target: DeviceTarget) -> str:
    script = f"{target.remote_root}/reCameraStart.py"
    venv = target.remote_venv
    return f"""[Desktop Entry]
Type=Application
Name=reCamera
Comment=Open reCamera dashboard
Exec=bash -c "source {venv}/bin/activate && exec python {script}"
Icon=utilities-terminal
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
StartupNotify=false
Terminal=false
"""


def render_desktop_shortcut(target: DeviceTarget) -> str:
    script = f"{target.remote_root}/reCameraStart.py"
    venv = target.remote_venv
    return f"""[Desktop Entry]
Type=Application
Name=reCamera
Comment=Open reCamera AI dashboard
Exec=bash -c "source {venv}/bin/activate && python {script}"
Icon=utilities-terminal
Terminal=false
"""


def deploy_one(target: DeviceTarget, dry_run: bool = False) -> None:
    print(f"\n=== 部署到设备: {target.name} ({target.user}@{target.host}) ===")
    check_reachable(target)

    if dry_run:
        print("dry-run，将上传以下文件:")
        for rel in CODE_FILES:
            print(f"  - {rel} -> {target.remote_root}/{rel}")
        print(f"  - autostart -> {target.remote_autostart}")
        print(f"  - desktop   -> {target.remote_desktop}")
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            target.host,
            port=target.port,
            username=target.user,
            password=target.password,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as exc:
        raise ConnectionError(
            f"SSH 登录失败 ({target.user}@{target.host})，请检查 IP、用户名和密码。详情: {exc}"
        ) from exc

    _, stdout, _ = client.exec_command("hostname", timeout=10)
    hostname = stdout.read().decode().strip()
    print(f"已连接远程主机: {hostname or target.host}")

    sftp = client.open_sftp()

    def upload_text(remote_path: str, content: str) -> None:
        parent = os.path.dirname(remote_path)
        try:
            sftp.stat(parent)
        except FileNotFoundError:
            client.exec_command(f"mkdir -p {parent}", timeout=10)
        with sftp.file(remote_path, "w") as remote_file:
            remote_file.write(content)
        print(f"updated {remote_path}")

    def upload_file(local_path: Path, remote_path: str) -> None:
        parent = os.path.dirname(remote_path)
        try:
            sftp.stat(parent)
        except FileNotFoundError:
            client.exec_command(f"mkdir -p {parent}", timeout=10)
        with local_path.open("rb") as src:
            with sftp.file(remote_path, "w") as dst:
                dst.write(src.read())
        print(f"updated {remote_path}")

    for rel in CODE_FILES:
        local_path = PROJECT_ROOT / rel.replace("/", os.sep)
        if not local_path.is_file():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        upload_file(local_path, f"{target.remote_root}/{rel}")

    upload_text(target.remote_autostart, render_autostart_desktop(target))
    upload_text(target.remote_desktop, render_desktop_shortcut(target))

    compile_cmds = " && ".join(
        [
            f"chmod 644 {target.remote_autostart}",
            f"chmod +x {target.remote_desktop}",
            f"python3 -m py_compile {target.remote_root}/reCameraStart.py",
            f"python3 -m py_compile {target.remote_root}/process/wifi_task.py",
            f"python3 -m py_compile {target.remote_root}/data/globalData.py",
        ]
    )
    _, out, err = client.exec_command(compile_cmds, timeout=30)
    exit_code = out.channel.recv_exit_status()
    if exit_code != 0:
        raise RuntimeError(err.read().decode() or "远程语法检查失败")

    sftp.close()
    client.close()
    print(f"deploy ok -> {target.name} ({target.host})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 ReCamera_start 部署到指定的 recomputer 设备",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python deploy/deploy_to_device.py --list
  python deploy/deploy_to_device.py --device recomputer-office
  python deploy/deploy_to_device.py --host 192.168.1.50 --device recomputer-office
  python deploy/deploy_to_device.py --device recomputer-office --dry-run

配置文件:
  优先读取 deploy/devices.local.json（本地，不入库）
  否则读取 deploy/devices.example.json

环境变量（可覆盖配置）:
  RECAMERA_DEPLOY_DEVICE, RECAMERA_DEPLOY_HOST, RECAMERA_DEPLOY_PORT
  RECAMERA_DEPLOY_USER, RECAMERA_DEPLOY_PASSWORD
        """.strip(),
    )
    parser.add_argument("--config", help="设备配置文件路径")
    parser.add_argument("--list", action="store_true", help="列出已配置设备")
    parser.add_argument("--device", "-d", help="设备名称（见 devices.local.json）")
    parser.add_argument("--host", help="覆盖配置中的 IP/主机名")
    parser.add_argument("--port", type=int, help="SSH 端口，默认 22")
    parser.add_argument("--user", "-u", help="SSH 用户名")
    parser.add_argument("--password", "-p", help="SSH 密码（也可用环境变量）")
    parser.add_argument("--remote-home", help="远程用户主目录，如 /home/seeed")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要部署的内容，不实际上传")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)

    try:
        config = load_config(config_path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        print("请先复制 deploy/devices.example.json 为 deploy/devices.local.json 并填写设备信息。", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.list:
        print(f"配置文件: {config_path}")
        list_devices(config)
        return

    try:
        target = build_target(
            config=config,
            device_name=args.device,
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            remote_home=args.remote_home,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc

    print(f"使用配置: {config_path}")
    try:
        deploy_one(target, dry_run=args.dry_run)
    except (ConnectionError, RuntimeError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(3) from exc


if __name__ == "__main__":
    main()
