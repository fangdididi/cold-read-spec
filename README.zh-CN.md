# 冷读规格（Cold-Read Spec）

[English](README.md) | **简体中文**

一个 AI 代理技能：在写代码**之前**先写功能规格，并证明一个没参加讨论的人也能照着它把东西做出来。

规格的作者看不见自己规格里的漏洞，因为记忆会自动补上。所以这个技能让第二个读者——一个零上下文的
新代理会话或子代理，只拿到规格文件——去回答作者事先写好的测验。每一个答错或回答“不在规格中”的问题，
都指向一句需要修改的话。冷读者通过后才开始写代码；代码对照编号实例、先写测试；合并前把每条需求都追踪到测试。

## 为什么需要

- AI 代理会严格照写的做，剩下的部分则充满自信地去猜。
- 新会话、新同事和未来的你，都没有参与产生这份规格的那段对话。
- 自己审自己的规格感觉很仔细，实际上几乎什么都发现不了。
- 代码悄悄长得比规格还多，下一次改动就没有可以对照的依据。

## 功能

- **可检查的规格结构**：带数字的问题、“完成标准”检查、“不做”围栏、术语表、带 必须/应当/可以 的需求 `R1..`、
  “假设/当/那么”形式的实例 `R1.a..`、决定 `D1..`、写明负责人的待定问题 `Q1..`。
- **格式检查**：缺实例、编号重复、没有数字的含糊词（如 “fast”“intuitive”“快速”“友好”）、
  没有可检查结果的实例、无人负责的问题、状态写 ready 却仍有待定问题。
- **冷读测验**：先写答案；新读者从四种视角之一作答（构建者、测试者、新人、质疑者）；
  自动评分为 MATCH / MISREAD / GAP，并列出要修改的规格编号。
- **修改循环规则**：改规格，绝不教读者；每轮换新读者；第三轮仍不通过就拆分功能。
- 对照实例编号**先写测试**，再用**追踪**找出没有测试的需求和 `DRIFT`（测试引用了规格里从未有过的编号）。
- 中英文规格都支持；只有一个 Python 文件，只用标准库，附 51 个测试。

## 安装

把整个文件夹复制到代理的技能目录。

| 代理 | 位置 |
| --- | --- |
| Claude Code | `~/.claude/skills/cold-read-spec/`（个人）或 `.claude/skills/cold-read-spec/`（项目） |
| Codex | `~/.codex/skills/cold-read-spec/` 或你的配置使用的技能目录 |
| Cursor | `.cursor/skills/cold-read-spec/`，或在项目规则里引用 `SKILL.md` |
| 其他代理 | 把 `SKILL.md`（或 `SKILL.zh-CN.md`）放到代理读取指令的位置，或粘贴进系统提示词 |

```bash
git clone https://github.com/fangdididi/cold-read-spec ~/.claude/skills/cold-read-spec
```

然后对代理说：“先给 CSV 导出写一份规格，冷读通过之后再动手。”

## 用法

```bash
# 1. 格式检查
python3 scripts/speccheck.py lint spec.md

# 2. 冷读评分（答案要在读者看到规格之前写好）
python3 scripts/speccheck.py quiz quiz-key.json cold-answers.json

# 3. 合并前：每条需求都有测试，没有测试引用不存在的编号
python3 scripts/speccheck.py trace spec.md tests/

# 任意命令加 --json 输出机器可读结果
```

`READY` / `PASS` / `TRACED` 时退出码为 `0`，其他结论为 `1`，输入有误为 `2`，可以直接用作 CI 关卡。

## 示例

```text
$ python3 scripts/speccheck.py lint examples/booking-reminder/spec.md
verdict: REVISE  (4 requirements, 4 examples, 2 open questions)
  [major] VAGUE R4 - Unmeasured words: 友好, 简单. Replace with a number or a check.
  [major] NO_OUTCOME R4.a - Example has no 'then ...' outcome a test could check.
  [major] UNOWNED_QUESTION Q2 - Open question has no owner (owner: name).

$ python3 scripts/speccheck.py trace examples/booking-reminder/spec.md examples/booking-reminder/tests
verdict: DRIFT
  R1 .../test_reminder.py
  R2 UNTESTED
  R3 .../test_reminder.py
  R4 UNTESTED
  examples with no test: R2.a, R4.a
  ORPHAN R6 in .../test_reminder.py (not in the spec: update the spec or remove the id)

$ python3 scripts/speccheck.py quiz examples/csv-export/quiz-key.json examples/csv-export/cold-answers.round1.json
verdict: FIX_SPEC  score 3/7, gaps 2, misreads 2
  ...
  fix these parts of the spec: D1, R1, R2, R3
```

`examples/csv-export/` 完整演示了：草稿 `BLOCKED` → 第一轮冷读 3/7 → 修改后的规格 `READY` → 新读者 7/7 `PASS` → `TRACED`。

## 文件结构

```text
cold-read-spec/
├── SKILL.md                    # 技能说明（英文）
├── SKILL.zh-CN.md              # 技能说明（中文）
├── README.md / README.zh-CN.md
├── LICENSE
├── scripts/speccheck.py        # lint / quiz / trace
├── templates/
│   ├── spec.md / spec.zh-CN.md # 空白规格模板
│   ├── quiz-key.json           # 答案模板
│   └── cold-reader-brief.md    # 给零上下文读者的任务说明（中英）
├── examples/
│   ├── csv-export/             # 草稿 → 第一轮冷读 → 修改后规格 → 第二轮 → 追踪
│   └── booking-reminder/       # 中文规格：REVISE 问题和 DRIFT 追踪
└── tests/test_speccheck.py     # 51 个测试：python3 -m unittest discover -s tests
```

## 许可证

MIT
