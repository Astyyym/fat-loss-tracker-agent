# 减脂记录 Agent

一个本地优先、单用户的饮食、运动、体重和腰围记录工具。支持 Hermes 原生调用、JSONL 事件溯源、纠错/删除/恢复、周报和只读网页仪表盘。

## 功能

- 自然语言记录饮食、运动、体重和腰围
- 热量与蛋白质估算、日汇总、周报和趋势
- JSONL 追加式事件：历史记录不会被静默覆盖
- `request_id` 幂等、重复记录提示和跨年纠错
- 原子写入、项目内备份、损坏行安全报错
- Windows / WSL 均可运行
- localhost 只读仪表盘，无 npm、数据库或外部 CDN

## 配置周期和目标

复制示例配置：

### Windows

```bat
copy config.example.json config.json
```

### Linux / WSL

```bash
cp config.example.json config.json
```

编辑 `config.json`：

```json
{
  "program_weeks": 8,
  "calorie_target_kcal": 1800,
  "training_day_calorie_max_kcal": 1900,
  "minimum_recommended_calories_kcal": 1500,
  "protein_target_g": 130,
  "protein_min_g": 120,
  "protein_max_g": 140,
  "timezone": "Asia/Shanghai"
}
```

`program_weeks` 可设置为 1–104。`config.json` 属于本地个人配置，已被 Git 忽略；公开仓库只包含 `config.example.json`。

不创建 `config.json` 时使用示例中的默认值。

## Hermes 接入

Hermes Skill 只需要把用户原文传给项目入口：

```bash
python3 backend/service.py '<用户原文>' --json --no-html
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

### 手动启动

Windows：

```bat
py -3 backend\server.py
```

Linux / WSL：

```bash
python3 backend/server.py
```

服务器固定绑定 `127.0.0.1`，不会自动暴露到局域网或公网。

## 命令行使用

```bash
python3 backend/service.py '早餐 标准早餐A'
python3 backend/service.py '体重 72.4kg，早起空腹'
python3 backend/service.py '运动 力量A 35分钟 完成'
python3 backend/service.py '减脂今天'
python3 backend/service.py '减脂本周复盘'
python3 backend/service.py '减脂趋势'
python3 backend/service.py '减脂表格'
```

JSON 输出：

```bash
python3 backend/service.py '减脂今天' --json --no-html
python3 backend/service.py --dashboard-json
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

```bash
python3 -m unittest discover -s tests -v
```

Windows：

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
tests/                   自动化测试
```

## 参考项目与链接

- [NousResearch/hermes-agent：Hermes Agent 官方仓库](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent 官方文档](https://hermes-agent.nousresearch.com/docs/)
- [Astyyym/fat-loss-tracker-agent：本项目 GitHub 仓库](https://github.com/Astyyym/fat-loss-tracker-agent)

本项目的 Hermes Gateway 接入与 Skill 路由方式参考了 Hermes Agent 的工具、技能和消息平台架构；减脂记录的数据模型、JSONL 事件机制和本地仪表盘由本项目实现。

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。你可以使用、复制、修改、合并、发布和分发本项目，但需保留原始版权及许可声明。
