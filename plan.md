# ToolTip 项目重构计划（修订版）

## 项目现状

- 当前 Git 跟踪文件：11 个；文本文件 10 个，约 1657 行；另有 `dist/AgentNotifyConfigurator.exe` 二进制产物。
- 主要源码：
  - `agent_notify_configurator.py`：约 640 行，GUI 组件、布局、状态、动作混在一起。
  - `agent_notify_core.py`：约 512 行，路径、JSON、Hook、安装卸载、PowerShell 模板混在一起。
- 当前测试：29 个测试通过，覆盖核心行为、GUI 静态结构、构建命令。
- 主要问题：
  - 模块职责不清，两个大文件承担过多责任。
  - PowerShell 模板内嵌在 core 中，阅读和测试成本高。
  - GUI 组件和 GUI 业务动作耦合。
  - 原计划存在循环导入风险：`AgentNotifyPaths` 不能留在 core 后再被 hooks 模块依赖。
- 技术债务重点：
  - 路径/配置/JSON 工具缺少底层模块。
  - Hook 合并逻辑可以独立成无 GUI、无脚本依赖的模块。
  - GUI 视觉组件可拆出，但步骤数据不单独薄拆。
  - 测试文件暂不拆分，避免过度碎片化。

## 重构目标

- 行为不变：Hook 输出、`config.json`、`notify.ps1`、GUI 功能入口保持一致。
- 对外入口不变：保留 `agent_notify_core.py` 对外可导入的核心函数和类名。
- 降低循环导入风险：底层路径/JSON/常量模块不依赖 core、hooks、GUI。
- 减少过度拆分：新增模块控制在 4 个以内。
- 保持小步可验证：每阶段独立测试、独立提交、可回退。

## 目标模块结构

- `agent_notify_config.py`
  - 承担底层配置能力。
  - 包含 `AgentNotifyPaths`、`default_paths()`、`read_json()`、`write_json()`、`backup_json()`、`MANAGED_BY`、`SUPPORTED_AUDIO_SUFFIXES`。
  - 不依赖 core、hooks、GUI。
- `agent_notify_hooks.py`
  - 承担 Hook 命令生成、托管 Hook 识别、合并、移除、状态检测。
  - 只依赖 `agent_notify_config.py`。
- `agent_notify_script.py`
  - 承担 `get_notify_script_content()`。
  - 只依赖必要常量，避免依赖 core。
- `agent_notify_ui_components.py`
  - 承担 `COLORS`、`FONT`、`IconCanvas`、`TimelineMarker`、`StepCard`、`StatusRow`。
  - 可同时放少量 GUI 步骤/状态文案 helper，不再单独创建 `agent_notify_ui_model.py`。
- `agent_notify_core.py`
  - 保留编排层：生成共享脚本、安装 Hook、卸载、运行测试通知、读取偏好、状态查询。
  - 从上述模块导入实现细节，并继续暴露原公共名称。
- `agent_notify_configurator.py`
  - 保留 `AgentNotifyApp`、GUI 布局编排、用户动作、loading、消息框。

## 重构步骤

### 第一阶段：写入计划与确认基线

**目标**：将本计划落盘为 `plan.md`，固定当前行为基线。
**依赖**：无。
**风险**：低。
**注意事项**：写入 `plan.md` 是规划文档动作，不修改业务行为。

**TODO**
- [x] 创建 `plan.md`，写入本计划。
- [x] 运行 `python -m pytest -q`，期望 29 passed。
- [x] 运行 `python -m compileall agent_notify_core.py agent_notify_configurator.py build_windows.py`。
- [x] 运行 `python agent_notify_configurator.py --self-test`。
- [x] 提交：`docs: add refactor plan`

### 第二阶段：抽出底层配置模块

**目标**：建立无循环依赖的底层模块，修复 DeepSeek 指出的核心风险。
**依赖**：第一阶段完成。
**风险**：低到中。
**注意事项**：不要把一次性字符串都提成常量；只迁移已有稳定概念。

**TODO**
- [x] 创建 `agent_notify_config.py`。
- [x] 从 `agent_notify_core.py` 移入 `AgentNotifyPaths`、`default_paths()`、`read_json()`、`write_json()`、`backup_json()`。
- [x] 移入 `MANAGED_BY`、`SUPPORTED_AUDIO_SUFFIXES`。
- [x] 在 `agent_notify_core.py` 中导入这些名称，保持旧模块仍可 `from agent_notify_core import AgentNotifyPaths`。
- [x] 运行 `python -m pytest tests/test_agent_notify_core.py -q`。
- [x] 提交：`refactor: extract config and path helpers`

### 第三阶段：抽出 Hook 逻辑

**目标**：让 Hook 处理独立于安装编排和脚本生成。
**依赖**：第二阶段完成。
**风险**：中。
**注意事项**：`agent_notify_hooks.py` 只从 `agent_notify_config.py` 导入，禁止导入 core。

**TODO**
- [ ] 创建 `agent_notify_hooks.py`。
- [ ] 移入 `build_hook_command()`、`is_managed_command()`、`make_hook_group()`、`remove_managed_hook_groups()`。
- [ ] 移入 `set_managed_hook()`、`remove_managed_hook()`、`is_event_configured()`、`as_list()`。
- [ ] `agent_notify_core.py` 从 hooks 模块导入这些函数。
- [ ] 全仓搜索残留引用：`rg "set_managed_hook|build_hook_command|is_event_configured"`。
- [ ] 运行 `python -m pytest tests/test_agent_notify_core.py -q`。
- [ ] 提交：`refactor: isolate hook configuration logic`

### 第四阶段：抽出通知脚本模板

**目标**：将大段 PowerShell 模板从 core 编排层移走。
**依赖**：第二阶段完成，可与第三阶段串行执行。
**风险**：中。
**注意事项**：脚本文本行为不能变；WPF toast、音频可选、VS Code 前台静默都必须保留。

**TODO**
- [ ] 创建 `agent_notify_script.py`。
- [ ] 移入 `get_notify_script_content()`。
- [ ] `agent_notify_core.py` 从 script 模块导入该函数。
- [ ] 保留现有 PowerShell parser 测试。
- [ ] 运行 `python -m pytest tests/test_agent_notify_core.py -q`。
- [ ] 做一次无音频 PowerShell 烟测。
- [ ] 提交：`refactor: isolate notification script template`

### 第五阶段：抽出 GUI 组件

**目标**：降低 `agent_notify_configurator.py` 体积，让 GUI 组件可单独阅读。
**依赖**：前面阶段完成后执行更稳。
**风险**：中。
**注意事项**：CustomTkinter 参数必须通过 GUI 启动烟测验证。

**TODO**
- [ ] 创建 `agent_notify_ui_components.py`。
- [ ] 移入 `COLORS`、`FONT`、`IconCanvas`、`TimelineMarker`、`StepCard`、`StatusRow`。
- [ ] 若需要步骤定义或状态文案 helper，放在同一文件，不新增 `agent_notify_ui_model.py`。
- [ ] 更新 `agent_notify_configurator.py` 导入。
- [ ] 运行 `python -m pytest tests/test_gui_layout.py -q`。
- [ ] GUI 启动 3 秒烟测，确认无 stderr。
- [ ] 提交：`refactor: extract configurator UI components`

### 第六阶段：清理 GUI 编排代码

**目标**：在不拆新文件的前提下，让 `AgentNotifyApp` 更易读。
**依赖**：第五阶段完成。
**风险**：中。
**注意事项**：不改按钮功能、不改文案策略、不改 Hook 调用。

**TODO**
- [ ] 将 `_build_timeline_steps()` 中步骤数据抽成同文件私有方法 `_step_definitions()`。
- [ ] 将右侧状态行更新逻辑抽成小方法 `_update_status_rows()`。
- [ ] 将 loading popup 布局抽成小方法 `_build_loading_popup()`，行为不变。
- [ ] 运行 `python -m pytest tests/test_gui_layout.py -q`。
- [ ] 运行 GUI 启动烟测。
- [ ] 提交：`refactor: simplify configurator app layout`

### 第七阶段：测试维护与 `.gitignore` 说明

**目标**：改进维护边界，不做不必要测试拆分。
**依赖**：前面阶段完成。
**风险**：低。
**注意事项**：测试文件暂不拆分；只更新导入和必要断言。

**TODO**
- [ ] 更新 `tests/test_agent_notify_core.py` 导入，保持行为覆盖不变。
- [ ] 更新 `tests/test_gui_layout.py`，避免过度依赖源码字符串。
- [ ] 在 `.gitignore` 增加注释：`dist/AgentNotifyConfigurator.exe` 当前作为发布产物被跟踪，`build/` 继续忽略。
- [ ] 运行 `python -m pytest -q`。
- [ ] 提交：`test: align tests with refactored modules`

### 第八阶段：文档和构建收尾

**目标**：让 README 与重构后的结构一致。
**依赖**：所有代码重构完成。
**风险**：低。
**注意事项**：先确认 README 文件编码，避免中文乱码。

**TODO**
- [ ] 检查 README UTF-8 显示。
- [ ] 更新文件结构说明。
- [ ] 保留“提示音可选”“只配置已安装工具”等现有行为说明。
- [ ] 运行 `python build_windows.py`。
- [ ] 运行最终验证：
  - `python -m pytest -q`
  - `python -m compileall agent_notify_core.py agent_notify_configurator.py build_windows.py`
  - `python agent_notify_configurator.py --self-test`
  - `git diff --check`
- [ ] 提交：`docs: update refactored project structure`

## 阶段总 TODOList

- [x] 阶段一：写入 `plan.md` 并确认基线
- [x] 阶段二：抽出 `agent_notify_config.py`
- [ ] 阶段三：抽出 `agent_notify_hooks.py`
- [ ] 阶段四：抽出 `agent_notify_script.py`
- [ ] 阶段五：抽出 `agent_notify_ui_components.py`
- [ ] 阶段六：清理 `AgentNotifyApp` 内部编排
- [ ] 阶段七：调整测试与 `.gitignore` 注释
- [ ] 阶段八：更新 README、构建 exe、最终验证

## 重构指导原则

- 行为不变是强约束。
- 对外入口名称保持不变。
- 数据契约保持不变。
- 每次只做一类结构性修改。
- 每阶段完成后立刻更新 `plan.md` TODO。
- 每阶段必须运行对应测试。
- 每阶段独立提交。
- 禁止引入无实际职责的薄模块。
- 禁止引入 core ↔ hooks 循环导入。
- 迁移代码尽量保留原变量名、错误文案、日志格式。
