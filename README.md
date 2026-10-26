![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)

# 赛博算命 Skill

基于 Claude Code 的八字排盘与命理分析工具。通过交互式对话收集出生信息，排出四柱八字，参照九本经典命理典籍进行专业分析。

## 功能

- **信息收集** — 逐步收集姓名、阳历/农历生日、出生时辰、性别、出生地等信息
- **排盘计算** — 自动排出年柱、月柱、日柱、时柱，计算大运与流年
- **综合分析** — 日主强弱、十神关系、五行平衡、格局判定、大运流年解读，以及事业、感情、健康等方面的建议

## 安装

> **注意**：Claude Code 从 git 仓库根目录的 `.claude/skills/` 查找 skill，请在正确的位置执行。本机需已安装 `python3`（只用标准库，无额外 pip 依赖）。

```bash
# 安装到当前项目（在 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/jinchenma94/bazi-skill .claude/skills/bazi

# 或安装到全局（所有项目都能用）
git clone https://github.com/jinchenma94/bazi-skill ~/.claude/skills/bazi
```

## 使用

在 Claude Code 中输入以下任意关键词即可触发：

`算八字` `看八字` `批八字` `排八字` `四柱` `命盘` `算命` `排盘` `bazi`

触发后，Skill 会逐步引导你提供出生信息，然后调用本仓库的排盘脚本并做综合分析。

排盘依赖本机 **python3**（3.6+ 即可），只用标准库，**无需 pip 安装任何第三方包**。确认出生信息后会执行：

```bash
python3 scripts/pai_pan.py --solar 1990-05-15 --shichen 午 --sex 男
```

### Windows / 中文乱码：用 run.sh

Windows 控制台默认 GBK，直接跑会遇到 `## ���` 这类乱码，`python3` 命令也常常不存在。用仓库自带的包装器，强制 UTF-8 并自动定位解释器：

```bash
scripts/run.sh --solar 1990-05-15 --hour 14:30 --sex 男 --place 杭州
scripts/run.sh --lunar 1990-04-21 --shichen 午 --sex 女 > 命盘.md
```

它会依次尝试 `$PYTHON` → `python3` → `python` → `py -3` → DSH 内置运行时，然后以 `PYTHONIOENCODING=utf-8` 执行 `pai_pan.py`，参数与直连完全一致。

### 自检：`scripts/doctor.sh`

排盘不出结果、乱码、或 skill 干脆没被加载时，先跑自检：

```bash
scripts/run.sh doctor          # 全量（含 11 个回归用例）
scripts/run.sh doctor --quick  # 跳过用例，秒出结果
```

| 检查项 | 抓什么 |
|---|---|
| 文件完整性 | SKILL.md / 脚本 / 5 份 references 缺失或为空 |
| front matter | 缺 `name`、缺闭合 `---`、正文标题被吞进头部（skill 静默不加载） |
| 行尾 | `.sh` 被转成 CRLF（bash 直接崩） |
| 解释器 | 找不到 Python 3.8+，或命中了 Windows Store 假 python |
| 编码 | 输出非 UTF-8、含替换字符、两次运行结果不一致 |
| 回归用例 | 排盘逻辑被改动、黄金值不命中 |
| 安装形态 | 位置非标准、`.dsh`/`.claude` 侧入口缺失、junction 断了 |

退出码：`0` 全通过，`1` 有 FAIL（技能不可用），`2` 仅 WARN（可用但有风险）。

## 参考典籍

| 典籍 | 简称 |
|------|------|
| 《穷通宝典》 | 论日主调候 |
| 《三命通会》 | 论格局神煞 |
| 《滴天髓》 | 论五行旺衰 |
| 《渊海子平》 | 论十神六亲 |
| 《千里命稿》 | 论命例实证 |
| 《协纪辨方书》 | 论择日神煞 |
| 《果老星宗》 | 论星命合参 |
| 《子平真诠》 | 论用神格局 |
| 《神峰通考》 | 论命理辨误 |

## 项目结构

```
bazi-skill/
├── SKILL.md                        # Skill 入口
├── scripts/
│   ├── pai_pan.py                  #   四柱/大运排盘（标准库，无 pip 依赖）
│   └── test_pai_pan.py             #   排盘回归测试
├── references/                     # 参考文件
│   ├── wuxing-tables.md            #   五行、天干地支、十神参考表
│   ├── shichen-table.md            #   时辰对照表、日上起时法
│   ├── dayun-rules.md              #   大运顺逆排规则、起运年龄计算
│   └── classical-texts.md          #   九本经典典籍核心规则摘要
├── LICENSE
└── README.md
```

## 免责声明

本 Skill 仅供传统文化学习与娱乐参考，分析结果不构成任何决策依据。命理学属于传统文化范畴，请理性看待。
