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
