# 减脂记录 Agent — Issue #1 Windows 本地回归验收与自检

## 1. 背景与产品边界

项目当前只承诺 **Windows 10/11 + Python 3.11+** 的本地运行。不要求用户安装 WSL，也不在公开 README、Skill 或示例中维护 Linux、WSL、macOS 的运行教程。

现有 Windows 启动器、服务和单元测试已经覆盖主要代码路径；本 Issue 的目标是补齐可重复执行的 Windows 自检与回归验证，尤其是中文/空格路径和日志隐私边界。

## 2. 目标

提供一个 Windows 原生自检入口，检查环境、项目可写性、端口状态、私有配置状态和 localhost 服务健康状况；并通过自动化测试验证脚本结构与隐私约束。

## 3. 功能范围

- 审计 Python、BAT、PowerShell、Skill、README，保持不依赖 `/mnt/*`、bash、`python3`、Linux 文件权限或 WSL 环境。
- 新增 Windows 自检脚本，至少检查：
  - Python 版本；
  - 项目目录可写性；
  - 8765 端口占用；
  - `profile.json` / `config.json` 的私有配置状态；
  - 已运行服务的 `/api/dashboard` 健康状态。
- 自检脚本不启动、停止或杀死服务，不写入健康事件。
- 启动器日志不得主动写入请求体、健康记录、Token 或项目绝对路径；失败信息以最小诊断为主。
- 自动化验证公开 Windows 入口不含 `/mnt/`、`python3`、`wsl`、bash 依赖。
- 自动化验证 BAT/PowerShell 的路径处理对中文和空格目录使用安全的根目录定位和引用方式。

## 4. 非目标

- 不恢复 Linux、WSL 或 macOS 的公开支持与教程。
- 不引入 Docker、数据库、云服务、账号系统或 GitHub Actions。
- 不创建第二个 Telegram Bot。
- 不在本 Issue 实现首次档案、通用 IM 协议或图片识别。
- 不把静态文本检查冒充为全新 Windows 机器上的 GUI 完整验收。

## 5. 验收标准

- [ ] `py -3 -m unittest discover -s tests -v` 通过。
- [ ] Windows 自检脚本能在 Windows PowerShell 下运行，并报告 Python、写权限、端口、配置和服务健康状态。
- [ ] `backend/service.py` 的 Windows 命令行记录与查询有自动化测试。
- [ ] 启动后 `/api/dashboard` 返回 200，停止后端口关闭的行为有现有脚本/测试覆盖；真实 Windows 冒烟结果单独记录。
- [ ] 公开启动入口和说明不包含 Linux、WSL、`python3`、`/mnt/` 或 bash 依赖。
- [ ] 中文、空格路径的安全引用逻辑有自动化检查；真实 Windows 目录冒烟结果单独记录。
- [ ] 公开跟踪文件、启动日志语义和测试 fixture 不包含真实健康数据、Token 或维护者绝对路径。
- [ ] `git diff --check` 通过。

## 6. AI Agent 开发边界

1. 保持 `backend/service.py` 为唯一业务和数据写入入口。
2. 不直接编辑或删除真实 JSONL 健康记录。
3. 不把健康数据、Token、chat ID、绝对路径写入测试或公开日志。
4. 所有新增公开命令使用 Windows `py -3` 或 PowerShell。
5. 每项实现先运行对应自动化测试，再运行全量测试和 Windows 冒烟。
6. 需求文档和开发短计划必须先更新，验证通过后才提交、推送和关闭 Issue。
