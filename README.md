# AI Hook 提示配置器

这是一个 Windows 桌面 GUI 工具，用来给 Codex 和 Claude Code 配置任务完成/等待确认提示。

它会生成共享通知脚本，自动合并用户级 Hook 配置，并支持一键取消配置。取消配置时只移除本工具写入的 Hook，同时删除 `C:\Users\用户名\.agent-notify` 托管目录。

## 文件

- `agent_notify_configurator.py`：GUI 程序入口，使用 customtkinter。
- `agent_notify_core.py`：Hook 合并、备份、取消配置、通知脚本生成等核心逻辑。
- `build_windows.py`：Windows 下用 PyInstaller 构建 EXE。
- `requirements.txt`：运行、测试和打包依赖。
- `tests/test_agent_notify_core.py`：核心行为测试。
- `dist/AgentNotifyConfigurator.exe`：构建后的可双击 GUI 程序。

## 使用 EXE

双击运行：

```text
dist\AgentNotifyConfigurator.exe
```

界面中按顺序操作：

1. 点击 `Browse` 选择一个 `.wav` 或 `.mp3` 提示音。
2. 点击 `Generate script` 生成共享通知脚本。
3. 点击 `Install hooks` 写入已安装工具的用户级 Hook 配置；如果只安装了 Codex 或只安装了 Claude Code，则只配置对应工具。
4. 点击 `Test notice` 测试声音和右下角通知。
5. 需要撤销时点击 `Uninstall`。

Codex 首次触发 Hook 时，可能还需要在 Codex 中通过 `/hooks` 信任该命令。

## 配置位置

工具会读写以下位置：

```text
C:\Users\用户名\.codex\hooks.json
C:\Users\用户名\.claude\settings.json
C:\Users\用户名\.agent-notify\
```

写入配置前，会自动给已有 JSON 文件生成备份：

```text
hooks.json.bak.YYYYMMDD-HHMMSS
settings.json.bak.YYYYMMDD-HHMMSS
```

重要规则：安装/写入配置前会先生成备份文件；只会写入已存在的 Codex/Claude 配置目录；取消配置不生成新备份，只移除本工具写入的 Hook 并删除托管目录。

## 安全边界

- 不覆盖 Claude/Codex 原有配置，只合并 `hooks` 字段。
- 安装/写入 Codex/Claude 配置前一定先备份原文件。
- 不展示或修改 Claude `env` 中已有的密钥配置。
- 重复安装不会重复追加本工具的 Hook。
- 取消配置只移除包含 `AgentNotifyConfigurator` 标记的 Hook。
- 删除目录前会校验目标目录名必须是 `.agent-notify`。
- 支持 WAV 和 MP3 音频；其他格式会直接报错，避免静默失败。

## 从源码运行

```powershell
python -m pip install -r requirements.txt
python agent_notify_configurator.py
```

## 构建 EXE

```powershell
python -m pip install -r requirements.txt
python build_windows.py
```

构建完成后生成：

```text
dist\AgentNotifyConfigurator.exe
```

## 验证

运行核心测试：

```powershell
python -m pytest tests/test_agent_notify_core.py -q
```

运行语法检查：

```powershell
python -m compileall agent_notify_core.py agent_notify_configurator.py build_windows.py
```
