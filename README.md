# 减脂记录 Agent

一个本地优先、单用户的饮食、运动、体重和腰围记录工具。支持 Hermes 原生调用、JSONL 事件溯源、纠错/删除/恢复、周报和只读网页仪表盘。

## 功能

- 自然语言记录饮食、运动、体重和腰围
- 热量与蛋白质估算、日汇总、周报和趋势
- JSONL 追加式事件：历史记录不会被静默覆盖
- `request_id` 幂等、重复记录提示和跨年纠错
- 原子写入、项目内备份、损坏行安全报错
- 面向 Windows 本地运行，提供一键启动和停止脚本
- localhost 只读仪表盘，无 npm、数据库或外部 CDN

## 首次设置与本地档案

首次打开仪表盘会显示设置向导。填写身高、当前体重、目标体重，并在**目标日期**与**计划周数**中二选一；系统将规范化保存计划起止日期和周数。

真实档案写入本机 `profile.json`，已被 Git 忽略。公开仓库只提供 [profile.example.json](profile.example.json)。热量与蛋白质属于估算建议，允许手动调整，不构成医疗建议。

旧版 `config.json` 仅作为一次性兼容来源读取可复用目标字段；它不会跳过首次设置。档案损坏时不会回退到默认目标，页面会明确报错。

修改个人目标不会改写历史 JSONL；仪表盘对历史记录的达标比较使用当前计划口径。

## 正式源码位置与环境

当前版本以 Windows 本地目录作为唯一正式源码位置。不要在其他位置保留可分别修改的重复仓库；需要迁移时通过 Git 完成，并明确唯一主副本。

## Hermes 接入

Hermes Skill 只需要把用户原文传给项目入口：

```bat
py -3 backend\service.py "<用户原文>" --json --no-html
```

可用表达：

```text
帮我记录一下：早餐 标准早餐A
减脂记录：午餐 鸡胸饭标准版
记录体重 72.4kg，早起空腹
运动 力量A 35分钟 完成
减脂今天
减脂本周复盘
减脂趋势
减脂表格
删除上一餐
刚才那顿是昨天的
```

项目本身不包含第二个 Telegram Bot，也不要求重复配置 Telegram Token 或 chat ID。Telegram 的连接和授权由现有 Hermes Gateway 负责。

### 通用 Agent / IM Gateway 协议

任何平台的 Gateway 都可通过 stdio JSON Lines 调用本地适配器：

```bat
py -3 backend\agent_adapter.py
```

每行传入一个 JSON 请求，核心字段是 `message`、可选稳定 `request_id`、`timezone` 和最小化 `attachments` 元数据。返回 `ok`、`markdown`、`event_ids`、`duplicate`、`error`、`kind`。适配器不保存 Token、chat ID、原始平台消息或图片二进制。

图片由用户已有的多模态 Agent 识别为候选结果后，可使用 `candidate_submit` 暂存候选；必须经 `candidate_confirm` 明确确认或修正后，才会写入饮食事件。项目不绑定任何视觉模型供应商。

### 安装附带的 Hermes Skill

仓库内附带公开版 Skill：

```text
skills/fat-loss-tracker/SKILL.md
```

将整个 Skill 目录复制到 Hermes 用户技能目录：

```bat
xcopy /E /I skills\fat-loss-tracker "%USERPROFILE%\.hermes\skills\productivity\fat-loss-tracker"
```

随后在 Hermes CLI 或 Gateway 中开启新会话，使 Skill 重新加载。公开版 Skill 不包含维护者本地路径；它会优先使用当前项目工作区，找不到项目时会要求用户提供克隆目录。

## 启动网页仪表盘

### Windows 双击启动

在项目根目录双击：

```text
启动减脂仪表盘.bat
```

浏览器会打开：

[本地减脂仪表盘](http://127.0.0.1:8765)

停止时双击：

```text
停止减脂仪表盘.bat
```

要求安装 Python 3.11 或更高版本。

首次使用或排查环境前，可双击：

```text
WindowsSelfCheck.bat
```

自检只检查 Python、项目写权限、8765 端口、私有档案状态和已运行服务的健康接口；不会写入任何健康记录，也不会启动或关闭服务。

启动器会把本地诊断日志写入 `runtime/logs/`。该目录已被 Git 忽略，不会上传到公开仓库。

> Windows 脚本结构、服务启动、接口访问、停止和端口释放已经完成验证；不同 Windows 机器上的 Python 安装状态仍可能影响启动。

### 手动启动

```bat
py -3 backend\server.py
```

服务器固定绑定 `127.0.0.1`，不会自动暴露到局域网或公网。

## 命令行使用

```bat
py -3 backend\service.py "早餐 标准早餐A"
py -3 backend\service.py "体重 72.4kg，早起空腹"
py -3 backend\service.py "运动 力量A 35分钟 完成"
py -3 backend\service.py "减脂今天"
py -3 backend\service.py "减脂本周复盘"
py -3 backend\service.py "减脂趋势"
py -3 backend\service.py "减脂表格"
```

JSON 输出：

```bat
py -3 backend\service.py "减脂今天" --json --no-html
py -3 backend\service.py --dashboard-json
```

## 数据机制

- 源事件：`data/YYYY.jsonl`
- 月度摘要：`summaries/YYYY-MM.md`
- 今日卡片：`cards/today.html`
- 滚动备份：`backups/YYYY/`

写入流程：跨平台排他锁 → 完整校验 → 项目内临时文件 → `fsync` → 备份 → 原子替换 → 全文件复检。

不要手工修改 JSONL 历史行。纠错、删除和恢复必须通过 `backend/service.py` 追加事件。

上述健康数据、摘要、卡片、备份和 `config.json` 均被 `.gitignore` 排除，不会随普通提交上传到公开仓库。

## 测试

```bat
py -3 -m unittest discover -s tests -v
```

测试覆盖 JSONL 校验、并发幂等、重复提示、更正/删除/恢复、跨年操作、原子写入、损坏文件、配置校验、HTML 转义、Markdown 降级、体重规则、周边界和 localhost 只读网页。

## 目录

```text
backend/service.py       唯一业务和数据读写入口
backend/server.py        localhost 只读 HTTP 服务
frontend/                本地仪表盘
config.example.json      可复制的公开配置示例
data/                    本地事件数据（Git 忽略）
summaries/ cards/        本地派生视图（Git 忽略）
backups/                 本地滚动备份（Git 忽略）
runtime/logs/             本地启动诊断日志（Git 忽略）
tests/                   自动化测试
skills/fat-loss-tracker/ 可安装的公开 Hermes Skill
docs/需求/               当前版本需求与开发边界
开发短计划/              当前计划与历史完成记录
```

## 参考项目与链接

- [NousResearch/hermes-agent：Hermes Agent 官方仓库](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent 官方文档](https://hermes-agent.nousresearch.com/docs/)
- [Astyyym/fat-loss-tracker-agent：本项目 GitHub 仓库](https://github.com/Astyyym/fat-loss-tracker-agent)

本项目的 Hermes Gateway 接入与 Skill 路由方式参考了 Hermes Agent 的工具、技能和消息平台架构；减脂记录的数据模型、JSONL 事件机制和本地仪表盘由本项目实现。

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。你可以使用、复制、修改、合并、发布和分发本项目，但需保留原始版权及许可声明。
