# AI Hook 提示配置器

这是一个 Windows 桌面 GUI 工具，用来给 Codex 和 Claude Code 配置任务完成/等待确认提示。

它会生成共享通知脚本，自动合并用户级 Hook 配置，并支持关闭窗口后驻留系统托盘。通知是否显示由应用里的总开关控制，取消配置时只移除本工具写入的 Hook，同时删除 `C:\Users\用户名\.agent-notify` 托管目录。

## 文件

```text
ToolTip/
|-- agent_notify_configurator.py    # GUI 程序入口、布局编排、用户动作
|-- agent_notify_ui_components.py   # GUI 视觉组件、图标、设置区块
|-- agent_notify_core.py            # 生成脚本、安装/取消 Hook、状态查询
|-- agent_notify_config.py          # 路径、配置、JSON 读写和稳定常量
|-- agent_notify_hooks.py           # Hook 命令生成、合并、移除和状态检测
|-- agent_notify_script.py          # 共享 PowerShell 通知脚本模板
|-- build_windows.py                # Windows 下用 PyInstaller 构建 EXE
|-- requirements.txt                # 运行、测试、托盘和打包依赖
|-- assets/
|   |-- lingxi_icon.svg             # 应用图标源文件
|   |-- lingxi_icon.ico             # Windows EXE/任务栏图标
|-- tests/
|   |-- test_agent_notify_core.py   # 核心行为测试
|   |-- test_build_windows.py       # 构建命令测试
|   |-- test_gui_layout.py          # GUI 静态结构测试
|   |-- test_readme.py              # README 结构测试
|-- dist/
|   |-- 灵犀提醒.exe                # 构建后的可双击 GUI 程序
```

## 使用 EXE

双击运行：

```text
dist\灵犀提醒.exe
```

主界面默认只展示常用设置：

1. `通知`：开启或暂停所有提醒。
2. `连接`：连接 Codex 与 Claude Code；如果只安装了 Codex 或只安装了 Claude Code，则只配置对应工具。
3. `提示音`：可选 `.wav` 或 `.mp3` 提示音；不选择时通知将静音显示。

低频操作在 `更多` 中：测试通知、生成脚本、复制配置摘要、查看诊断日志、撤销配置。

关闭主窗口不会退出程序，灵犀提醒会隐藏到系统托盘。托盘菜单只提供 `打开主面板`、`开启/关闭通知`、`退出程序`。

Codex 首次触发 Hook 时，可能还需要在 Codex 中通过 `/hooks` 信任该命令。

## 通知排查

通知只受总开关控制：开启通知时会尝试弹框，关闭通知时会跳过弹框和声音。脚本会在 `C:\Users\用户名\.agent-notify\notify.log` 记录诊断结果：

- `triggered`：Hook 已经调用通知脚本。
- `shown`：通知弹框已显示。
- `skipped-disabled`：通知总开关关闭，因此跳过。
- `audio-error`：提示音失败，但不会阻止弹框。

如果 Claude 有日志而没有 Codex 日志，通常说明 Codex 没有读取或触发 `C:\Users\用户名\.codex\hooks.json` 中的 Hook，而不是通知脚本被静默拦截。此时优先检查 Codex 中 `/hooks` 的信任状态、当前 Windows 用户目录，以及实际启动 Codex 时使用的配置位置。

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
- 诊断日志只记录通知来源、事件和展示/跳过结果，不记录密钥、环境变量或用户输入。

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
dist\灵犀提醒.exe
```

## 验证

运行核心测试：

```powershell
python -m pytest tests/test_agent_notify_core.py -q
```

运行语法检查：

```powershell
python -m compileall agent_notify_config.py agent_notify_hooks.py agent_notify_script.py agent_notify_core.py agent_notify_ui_components.py agent_notify_configurator.py build_windows.py
```
