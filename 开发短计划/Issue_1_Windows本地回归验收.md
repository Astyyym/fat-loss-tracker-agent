# Issue #1 — Windows 本地回归验收短计划

**需求依据：** `docs/需求/Issue_1_Windows本地回归验收_PRD.md`

## 任务 1：重写 GitHub Issue 范围
- 文件：GitHub Issue #1。
- 步骤：移除保留 Linux/WSL 支持的旧要求；明确 Windows-only 产品边界、可复现自检范围和验收标准。
- 验证：Issue 内容与当前 README/公开 Skill 的 Windows-only 定位一致。

## 任务 2：增加 Windows 自检入口
- 文件：`Windows环境自检.ps1`、`Windows环境自检.bat`、`tests/test_windows_launcher.py`。
- 步骤：检查 Python、目录写权限、8765 端口、私有配置状态与已运行服务健康状态；不写健康数据、不干预服务生命周期。
- 验证：脚本可在 Windows PowerShell 调用；自动化测试覆盖入口、路径和无敏感输出约束。

## 任务 3：补足可复现测试
- 文件：`tests/test_windows_launcher.py`、必要的服务测试。
- 步骤：验证 Windows 命令、路径引用、公开说明和日志约束；保留现有启动/停止行为测试。
- 验证：`py -3 -m unittest discover -s tests -v` 通过。

## 任务 4：Windows 冒烟与交付
- 文件：全部本轮改动。
- 步骤：运行自检、服务启动/停止、`/api/dashboard` 健康检查、全量测试、敏感扫描、`git diff --check`；提交推送后关闭 Issue #1。
- 验证：远程 `main` 与本地提交一致；Issue 关闭说明包含真实验证证据与尚未覆盖的边界。
