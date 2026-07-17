# 四周减脂记录 Agent

这是一个由 **Hermes 原生调用**的单用户饮食、运动、体重和腰围记录工具。日常直接在已经连接 Hermes 的 Telegram 对话中记录，不需要本项目单独配置 Telegram Token 或 chat ID。

```text
现有 Hermes Telegram Bot → Hermes Gateway → fat-loss-tracker Skill
                                          ↓
                                backend/service.py
                                          ↓
                                  data/YYYY.jsonl
```

唯一可信源是 `data/YYYY.jsonl`。修改、删除和恢复全部追加事件，不覆盖历史记录。

## 日常怎么使用

在现有 Hermes Telegram 对话里直接说：

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

Hermes 的 `fat-loss-tracker` Skill 会调用本项目的 `backend/service.py`。本项目不再包含或运行第二个 Telegram Bot。

为避免误触发，单独说“今天”“趋势”“表格”且上下文明显与减脂无关时，不应调用本项目；使用“减脂今天”“今日饮食汇总”等表达最明确。

> 新创建的 Skill 通常在新会话加载。Telegram 中发送 `/new` 或 `/reset` 后再开始使用。

## 打开本地网页

在 Windows 资源管理器打开：

```text
D:\wenjian\Hermes\四周减脂记录Agent\
```

双击：

```text
启动减脂仪表盘.bat
```

脚本会使用 Windows Python 启动只读服务器，并自动打开：

[本地减脂仪表盘](http://127.0.0.1:8765)

停止时双击：

```text
停止减脂仪表盘.bat
```

要求 Windows 已安装 Python 3.11 或更高版本。脚本优先使用 `py -3`，没有 Python 时会明确提示。

网页固定绑定 `127.0.0.1`，不会公开到局域网或互联网。页面只读，不使用 LocalStorage 保存业务数据。

## 也可以手动启动

### Windows

```bat
cd /d D:\wenjian\Hermes\四周减脂记录Agent
py -3 backend\server.py
```

### WSL

```bash
cd '/mnt/d/wenjian/Hermes/四周减脂记录Agent'
python3 backend/server.py
```

## 命令行调用

Windows：

```bat
py -3 backend\service.py "早餐 标准早餐A"
py -3 backend\service.py "今天"
```

WSL：

```bash
python3 backend/service.py '早餐 标准早餐A'
python3 backend/service.py '今天'
```

JSON 输出：

```bash
python3 backend/service.py '今天' --json --no-html
python3 backend/service.py --dashboard-json
```

## 数据机制

- 源事件：`data/YYYY.jsonl`
- 月度摘要：`summaries/YYYY-MM.md`
- 最近今日卡片：`cards/today.html`
- 滚动备份：`backups/YYYY/`

写入流程：

1. 获取跨 Windows/WSL 项目锁 `data/.write.lock`
2. 校验现有 JSONL
3. 写入项目内临时文件并 `fsync`
4. 备份旧文件
5. 原子替换
6. 复检每一行

损坏 JSONL 会报告行号并备份损坏文件，不会被显示成“没有记录”。派生卡片或摘要失败时，已落盘的源事件不会回滚，后端会返回 Markdown 降级提示。

不要手工修改 JSONL 历史行。纠错、删除和恢复必须通过 `backend/service.py` 追加 `correction`、`delete`、`restore` 事件。

## 恢复备份

Windows 示例：

```bat
py -3 -c "from backend.service import CalorieService; print(CalorieService().restore_backup(r'backups\2026\备份文件名.jsonl'))"
```

恢复前会校验备份，并先备份当前源文件。

## 测试

WSL：

```bash
cd '/mnt/d/wenjian/Hermes/四周减脂记录Agent'
python3 -m unittest discover -s tests -v
```

Windows：

```bat
cd /d D:\wenjian\Hermes\四周减脂记录Agent
py -3 -m unittest discover -s tests -v
```

覆盖 JSONL 校验、并发幂等、重复提示、更正/删除/恢复、跨年操作、原子写入、损坏文件、HTML 转义、Markdown 降级、体重规则、周边界和 localhost 只读网页。

## 目录职责

```text
backend/service.py       唯一业务与数据读写入口
backend/server.py        localhost 只读 HTTP 服务
frontend/                本地只读仪表盘
data/                    唯一源事件
summaries/ cards/        可重建派生视图
backups/                 项目内滚动备份
tests/                   自动化验收
启动减脂仪表盘.bat       Windows 双击启动
停止减脂仪表盘.bat       Windows 双击停止
```

项目不保存 Telegram Token、chat ID，也没有独立 Telegram 网关。
