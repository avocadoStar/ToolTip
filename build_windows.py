from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


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
        "AgentNotifyConfigurator",
        "--collect-all",
        "customtkinter",
        "--hidden-import",
        "darkdetect",
        str(ROOT / "agent_notify_configurator.py"),
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

    old_exe = dist_dir / "AgentNotifyConfigurator.exe"
    if old_exe.exists():
        old_exe.unlink()

    command = build_pyinstaller_command(pyinstaller_exe)
    print("[RUN]", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"Created {old_exe.resolve()}")


if __name__ == "__main__":
    main()
