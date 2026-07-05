![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)
![Platform: Windows/macOS/Linux](https://img.shields.io/badge/Platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Version: 3.0](https://img.shields.io/badge/Version-3.0-orange)

# 赛博算命 Skill v3.0 — 八字 + 运势 + 健康

基于 Claude Code / OpenClaw 的**八字排盘 + 8 维度运势 + 4 维度健康**综合分析工具。

v3.0 新增：调用 `scripts/fortune_health.py` 确定性算法（**不依赖 LLM**），1-5 星评分 + 五行→脏腑映射。

## 功能

- **基础排盘** — 阳历/农历生日、出生时辰、性别、出生地
- **真太阳时校正** — 基于经度差，自动校正 ±30 分钟内
- **综合分析** — 日主强弱、十神关系、五行平衡、格局判定、大运流年
- **典籍引证** — 9 本经典命理典籍
- **8 维度运势（新）** — 今日 / 本周 / 本月 / 本年
- **4 维度健康（新）** — 今日 / 节气 / 季节 / 本年
- **确定性算法（新）** — Python 脚本计算，无 LLM 幻觉

## 触发词

**基础**：`测八字` `算命` `排八字` `看命` `bazi` `八字测算` `生辰八字` `四柱` `算一卦` `看看八字`

**运势**：`今日运势` `本周运势` `本月运势` `本年运势` `运势怎么样` `运程`

**健康**：`身体健康` `健康状况` `节气养生` `季节健康` `年度健康` `脏腑`

## 输入

4 个必填字段：
```
1990-05-15 10:30 阳历 男 辽宁省丹东市
```

或更口语化：
```
阳历 1990 年 5 月 15 日 上午 10 点半，男，辽宁丹东
```

## 输出示例

```
🪞 四柱八字极速测算 + 运势健康
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 出生：1990 年 5 月 15 日 10:30（阳历）
...

【四柱】
年柱：庚午  月柱：辛巳  日柱：甲子 ⬅️ 日主 = 甲木  时柱：己巳

【运势 4 维度】
【今日运势】(2026-06-29 甲戌日)
整体：★★★☆  事业：★★★☆  财运：★★★☆  感情：★★★☆  人际：★★★½

【本周运势】(6-29 ~ 7-05)
整体：★★★  最吉：6-30 丙子日  最凶：7-02 戊寅日

【本月运势】(2026-06)
月柱 庚午 + 流年 丙午 → ★★☆

【本年运势】(2026 丙午年)
流年：★☆

【健康 4 维度】
【今日健康】土气受制 → 重点：脾/胃
【节气健康】夏至 火气受制 → 重点：心/小肠
【季节健康】夏季 火当令 → 重点：心/小肠
【年度健康】2026 火气受制 → 重点：心/小肠
```

## 安装

### Claude Code（本地）

```bash
mkdir -p .claude/skills
git clone https://github.com/jinchenma94/bazi-skill .claude/skills/bazi
```

### OpenClaw

```bash
cp -r bazi-fortune ~/.openclaw/skills/

# 或一键部署
cd bazi-fortune && bash deploy.sh
```

## 算法说明

### 8 维度计算逻辑

| 维度 | 时间单位 | 评分基础 |
|------|---------|---------|
| 今日运势 | 日柱 | score_gz_to_chart(今日日柱, 八字) + 十神 bonus |
| 本周运势 | 7 日柱 | 平均分 + 最吉/最凶日 |
| 本月运势 | 月柱 + 流年 | 加权 0.6/0.4 |
| 本年运势 | 流年 | score_gz_to_chart(流年, 八字) |
| 今日健康 | 日支五行 | 五行→脏腑 + 喜忌判定 |
| 节气健康 | 当前节气 | 同上（24 节气） |
| 季节健康 | 春/夏/秋/冬 | 同上（4 季） |
| 年度健康 | 流年天干 | 同上（流年） |

### 喜忌神判定

| 日主 | 喜神 | 忌神 |
|------|------|------|
| 身旺 | 食伤 + 财 + 官杀 | 印 + 比劫 |
| 身弱 | 印 + 比劫 | 食伤 + 财 + 官杀 |

### 五行 → 脏腑

| 五行 | 脏 | 腑 | 部位 |
|------|-----|-----|------|
| 木 | 肝 | 胆 | 目/筋/爪甲 |
| 火 | 心 | 小肠 | 舌/血脉/面部 |
| 土 | 脾 | 胃 | 口/唇/肌肉 |
| 金 | 肺 | 大肠 | 鼻/皮肤/毛发 |
| 水 | 肾 | 膀胱 | 耳/骨骼/头发 |

详见 `references/fortune-health-rules.md`。

## 项目结构

```
bazi-fortune/
├── SKILL.md                          # Skill 入口（v3.0 运势健康版）
├── README.md                         # 本文件
├── requirements.txt                  # Python 依赖（sxtwl）
├── LICENSE                           # MIT 协议
├── deploy.sh                         # 一键部署 + 冒烟测试
├── references/                       # 参考文件
│   ├── wuxing-tables.md              #   五行、天干地支、十神
│   ├── shichen-table.md              #   时辰对照、五鼠遁
│   ├── dayun-rules.md                #   大运顺逆排规则
│   ├── classical-texts.md            #   9 本典籍核心规则
│   └── fortune-health-rules.md       #   8 维度运势 + 4 维度健康规则
├── scripts/                          # 确定性算法
│   └── fortune_health.py             #   运势 + 健康计算引擎
└── tests/                            # （可选）回归测试
    └── test_fortune_health.py
```

## 云端部署（Linux）

### 1. 安装系统依赖
```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y gcc python3-dev python3-pip

# CentOS/RHEL
sudo yum install -y gcc python3-devel
```

### 2. 一键部署
```bash
cd bazi-fortune && bash deploy.sh
```

**注意**：`sxtwl` 是 C 扩展，**PyPI 没有 Linux/macOS wheel**，需源码编译。
若编译失败，用纯 Python 替代：
```bash
pip install lunar-python
```

### 3. 部署到 OpenClaw
```bash
cp -r bazi-fortune ~/.openclaw/skills/
ls ~/.openclaw/skills/bazi-fortune/
# 应看到: SKILL.md README.md requirements.txt LICENSE references/ scripts/
```

## 跨平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows 10/11 | ✅ 已验证 | Python 3.13 + sxtwl 2.0.7 |
| Linux (Ubuntu 22.04) | ⚠️ 需 gcc | sxtwl 源码编译 |
| macOS | ⚠️ 需 Xcode CLI | `xcode-select --install` |

## 局限性

1. **节气日期精度**：当前实现按月日阈值近似，±1-2 天偏差
2. **大运交互**：本年运势暂未叠加当前大运
3. **空亡/神煞**：未实现（暂不纳入）
4. **起运年龄**：本算法只算当前大运，暂不计算具体流年交接

如需更高精度，建议参考 `references/classical-texts.md` 中 9 本典籍的进阶规则。

## 免责声明

本 Skill 仅供传统文化学习与娱乐参考，分析结果不构成任何决策依据。

- 如涉及健康：**以医学诊断为准**
- 如涉及财务：理性决策，避免投机
- 命理学属于传统文化范畴，请理性看待

## 版本

- **v3.0（运势健康版）** — 新增 8 维度运势 + 4 维度健康，调用 `scripts/fortune_health.py` 确定性计算
- **v2.0（极简版）** — 4 字段输入，无交互，立即出结果
- **v1.0（交互版）** — 原 jinchenma94/bazi-skill 风格，分步询问

## Fork 与 PR 状态

本仓库为 [jinchenma94/bazi-skill](https://github.com/jinchenma94/bazi-skill) 的 fork，v3.0 已提交 PR：

- **PR #20**: <https://github.com/jinchenma94/bazi-skill/pull/20>
- **状态**: open ✅ / mergeable ✅ / clean ✅ / 0 comments（等 maintainer review）
- **提交时间**: 2026-06-29
- **变更量**: +1792 / -232 across 9 files

如果你是 maintainer，可以直接合并。如果你想跟进评论，草稿见本地 `PR_COMMENT.md`（不提交到 repo，避免污染 PR diff）。
