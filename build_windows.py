from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_NAME = "灵犀提醒"
LEGACY_APP_NAME = "AgentNotifyConfigurator"
ICON_PATH = ROOT / "assets" / "lingxi_icon.ico"


def resolve_command(*candidates: str) -> str:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise FileNotFoundError(f"Cannot find command: {' / '.join(candidates)}")


def build_pyinstaller_command(pyinstaller_exe: str) -> list[str]:
    return [
        pyinstaller_exe,
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--icon",
        str(ICON_PATH),
        "--add-data",
        f"{ICON_PATH};assets",
        "--collect-all",
        "customtkinter",
        "--collect-all",
        "pystray",
        "--collect-all",
        "PIL",
        "--hidden-import",
        "darkdetect",
        "--hidden-import",
        "pystray._win32",
        str(ROOT / "agent_notify_configurator.py"),
    ]


def release_exe_paths(dist_dir: Path) -> list[Path]:
    return [
        dist_dir / f"{LEGACY_APP_NAME}.exe",
        dist_dir / f"{APP_NAME}.exe",
    ]


def release_spec_paths(root: Path) -> list[Path]:
    return [
        root / f"{LEGACY_APP_NAME}.spec",
        root / f"{APP_NAME}.spec",
    ]


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("This build script is intended for Windows.")

    pyinstaller_exe = resolve_command("pyinstaller.exe", "pyinstaller")
    build_dir = ROOT / "build"
    dist_dir = ROOT / "dist"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    dist_dir.mkdir(exist_ok=True)

    for old_exe in release_exe_paths(dist_dir):
        if old_exe.exists():
            old_exe.unlink()
    for old_spec in release_spec_paths(ROOT):
        if old_spec.exists():
            old_spec.unlink()

    command = build_pyinstaller_command(pyinstaller_exe)
    print("[RUN]", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"Created {(dist_dir / f'{APP_NAME}.exe').resolve()}")


if __name__ == "__main__":
    main()
