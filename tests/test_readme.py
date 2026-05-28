from __future__ import annotations

from pathlib import Path


def test_readme_files_section_uses_directory_tree() -> None:
    readme = Path("README.md").read_text(encoding="utf-8-sig")
    files_section = readme.split("## 文件", 1)[1].split("## 使用 EXE", 1)[0]

    assert "```text" in files_section
    assert "ToolTip/" in files_section
    assert "|-- agent_notify_configurator.py" in files_section
    assert "|-- agent_notify_ui_components.py" in files_section
    assert "|-- agent_notify_script.py" in files_section
    assert "|-- assets/" in files_section
    assert "|   |-- lingxi_icon.svg" in files_section
    assert "|-- tests/" in files_section
    assert "|-- dist/" in files_section
    assert "|   |-- 灵犀提醒.exe" in files_section
