# 八字命理 Skill

基于 Claude / Claude Code 的四柱八字命理分析工具，集合传统典籍与现代流派，覆盖八字分析、合婚、择日、姓名学等完整应用场景。

## ✨ 核心功能

- **信息收集** — 交互式收集出生信息（含真太阳时、性别、出生地）
- **排盘计算** — 年月日时四柱 + 大运 + 流年
- **多流派分析** — 支持六大流派的特色分析
- **调候 + 格局 + 病药** — 四大经典体系综合
- **合婚 / 择日 / 姓名** — 三大实用模块
- **历史事件校准** — 提高分析准确度

## 🚀 快速开始

### 安装

```bash
mkdir -p .claude/skills
git clone https://github.com/fckcg/bazi-skill .claude/skills/bazi
```

### 使用

在 Claude Code 中输入触发词：

| 场景 | 触发词 |
|------|-------|
| 八字分析 | `算八字` / `看八字` / `排盘` / `bazi` |
| 合婚 | `合婚` / `看两个人合不合` / `八字配对` |
| 择日 | `择日` / `看吉日` / `看结婚日期` / `看开张日期` |
| 起名 | `起名` / `改名` / `姓名分析` |

## 📊 支持的分析流派

| 流派 | 核心方法 | 代表人物/典籍 |
|------|---------|-------------|
| 🏛️ 经典派 | 格局 + 用神 + 调候 + 病药 | 《子平真诠》《滴天髓》《穷通宝典》《神峰通考》 |
| 🌿 徐五行派 | 五行平衡调理 | 现代实用派 |
| 💭 李涵辰新派 | 宾主说 + 十神定位 + 五行反断 | 李涵辰《四柱预测学》 |
| 🎯 港台派 | 大运流年实战预测 | 梁湘润、钟义明、李居明 |
| 🧠 心理派 | 命理与心理学结合 | 何建忠《八字心理推命学》 |
| 🔄 混合派 | 综合多流派优点 | 360° 全面诊断 |

另含**盲派命理**独立章节（段建业、王庆等代表）。

## 📁 项目结构

```
bazi-skill/
├── SKILL.md                              主流程
├── references/
│   ├── 【哲学总章】
│   │   └── yijing-foundation.md          易经总纲：阴阳/五行/河图洛书/八卦
│   │
│   ├── 【经典流派】
│   │   ├── classical-texts.md            基础典籍规则
│   │   ├── zipin-zhenquan-sishen.md      子平真诠四神体系
│   │   ├── shenfeng-bingyao.md           神峰通考病药说
│   │   ├── tiaohou-yongshen.md           穷通宝典调候120条
│   │   ├── manpai-school.md              盲派命理完整指南
│   │   ├── li-hanchen-school.md          李涵辰新派
│   │   ├── hong-kong-taiwan-school.md    港台派
│   │   ├── xu-wuxing-school.md           徐五行派
│   │   └── psychology-school.md          心理派
│   │
│   ├── 【基础排盘】
│   │   ├── shichen-table.md / zhen-taiyang-shi.md
│   │   ├── dayun-rules.md / dayun-liuyear-interaction.md
│   │   ├── wuxing-tables.md / dizhi-canggan.md
│   │   ├── tiangan-heke.md / xing-chong-he-hai.md
│   │   ├── nayin-wuxing.md / kongwang.md
│   │   └── taiyuan-minggong.md
│   │
│   ├── 【分析核心】
│   │   ├── bazi-strength-rating.md       日主旺衰评分
│   │   ├── choosing-yongshen.md          用神确定完全指南
│   │   ├── shishen-analysis.md           十神分析
│   │   ├── shishen-combinations.md       十神宫位组合
│   │   ├── shishen-taboos.md             十神禁忌
│   │   └── special-formats.md            特殊格局
│   │
│   ├── 【神煞与断语】
│   │   ├── shensha-complete-system.md    神煞完整系统
│   │   ├── shensha-guide.md              神煞速查
│   │   ├── shensha-by-schools.md         各流派神煞用法
│   │   └── classic-duanyu.md             经典断语口诀
│   │
│   ├── 【应用专题】
│   │   ├── nvming-zhuanlun.md            女命专论
│   │   ├── hehun.md                      八字合婚
│   │   ├── zeri.md                       择日学
│   │   └── xingming-bazi.md              姓名学与八字配合
│   │
│   ├── 【流派对照与辅助】
│   │   ├── schools-framework.md          六大流派框架
│   │   ├── schools-comparison.md         流派对比详表
│   │   ├── school-selection-guide.md     流派选择指南
│   │   └── master-methods.md             名家方法论
│   │
│   ├── 【实战与反馈】
│   │   ├── case-examples.md              实战案例
│   │   ├── quick-diagnosis.md            快速诊断模式
│   │   ├── user-feedback-system.md       历史事件校准
│   │   └── faq.md                        常见问题
│   │
│   └── 【工程索引】
│       ├── glossary.md                   术语词典（按拼音）
│       └── bibliography.md               参考书目总索引
│
├── LICENSE                               MIT 开源协议
└── README.md                             本文件
```

## 🎯 适用人群

- 对中国传统命理学感兴趣的爱好者
- 希望借助 AI 辅助学习八字的学习者
- 需要结合命理参考做决策的用户
- 研究中国传统文化的研究者

## ⚖️ 免责声明

- 本 Skill 仅供**传统文化学习与参考**
- 命理分析结果仅作参考，**不构成任何专业决策建议**（医疗、法律、投资等专业问题请咨询相应专业人士）
- 反对用命理制造焦虑、诱导消费、替代专业判断
- 强调"知命立命"：命理是了解自己的工具，不是决定命运的判决

## 🤝 贡献

欢迎 PR！本项目坚持：
- **学术严谨**：每个论断都有典籍或理论依据
- **语义中立**：不迷信、不恐吓、不商业化
- **现代视角**：去除传统中的性别歧视、宿命论色彩
- **批判思维**：保留、改造、摒弃传统内容分层处理

## 📜 许可证

MIT License — 详见 LICENSE
