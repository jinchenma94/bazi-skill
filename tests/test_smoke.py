"""bazi-fortune 8 维度冒烟测试 - 5 个 case × 8 维度"""
import sys
import json
from pathlib import Path
from datetime import date

_BASE = Path(r'C:\Users\Luiki\.openclaw\workspace')
sys.path.insert(0, str(_BASE / 'skills' / 'bazi-fortune' / 'scripts'))

from fortune_health import generate_full_report, format_markdown, get_daymaster_strength, get_xishen_jishen

# 5 个测试 case
test_cases = [
    {
        "label": "1990-05-15 10:30 男 辽宁丹东 (SKILL.md example)",
        "chart": {
            "年柱": ("庚", "午"),
            "月柱": ("辛", "巳"),
            "日柱": ("甲", "子"),
            "时柱": ("己", "巳"),
        },
        "expected_strength": "弱",  # 甲木生巳月失令
    },
    {
        "label": "1987-06-11 8:43 女 博白",
        "chart": {
            "年柱": ("丁", "卯"),
            "月柱": ("壬", "午"),
            "日柱": ("丙", "子"),
            "时柱": ("壬", "辰"),
        },
        "expected_strength": None,  # 任意
    },
    {
        "label": "1985-08-20 男 北京 (秋金旺)",
        "chart": {
            "年柱": ("乙", "丑"),
            "月柱": ("甲", "申"),
            "日柱": ("庚", "午"),
            "时柱": ("辛", "巳"),
        },
        "expected_strength": None,
    },
    {
        "label": "1992-03-08 23:30 男 北京 (春木)",
        "chart": {
            "年柱": ("壬", "申"),
            "月柱": ("癸", "卯"),
            "日柱": ("甲", "子"),
            "时柱": ("甲", "子"),
        },
        "expected_strength": "旺",  # 甲木 + 卯月 + 2 子水生
    },
    {
        "label": "1980-12-15 男 哈尔滨 (冬水旺)",
        "chart": {
            "年柱": ("庚", "申"),
            "月柱": ("戊", "子"),
            "日柱": ("壬", "寅"),
            "时柱": ("辛", "亥"),
        },
        "expected_strength": "旺",  # 壬水 + 子月 + 亥
    },
]

# 跑测试
print("=" * 60)
print("bazi-fortune 8 维度冒烟测试")
print("=" * 60)

target = date(2026, 6, 29)
print(f"测试日期: {target}\n")

passed = 0
failed = 0

for i, tc in enumerate(test_cases, 1):
    print(f"[Case {i}] {tc['label']}")
    chart = tc["chart"]
    dm = chart["日柱"][0]
    dm_wx_map = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                 "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
    print(f"  日主: {dm}({dm_wx_map[dm]})")

    # 强弱
    strength = get_daymaster_strength(chart)
    xishen, jishen = get_xishen_jishen(chart)
    print(f"  强弱: {strength}, 喜: {xishen or '中'}, 忌: {jishen or '中'}")

    if tc["expected_strength"] and strength != tc["expected_strength"]:
        print(f"  ⚠️  expected {tc['expected_strength']}, got {strength}")
    else:
        print(f"  ✅ 强弱判定符合预期")

    # 8 维度报告
    try:
        report = generate_full_report(chart, target)
        required_dims = [
            ("运势", "今日"), ("运势", "本周"), ("运势", "本月"), ("运势", "本年"),
            ("健康", "今日"), ("健康", "节气"), ("健康", "季节"), ("健康", "本年"),
        ]
        ok = True
        for cat, dim in required_dims:
            if cat not in report or dim not in report[cat]:
                print(f"  ❌ {cat}/{dim} 缺失")
                ok = False
        if ok:
            # 详细输出
            fy = report["运势"]
            jk = report["健康"]
            print(f"  ✅ 8 维度完整")
            print(f"    今日: {fy['今日']['干支']}日 / 整体{fy['今日']['维度']['整体']}星")
            print(f"    本周: {fy['本周']['周开始']}~{fy['本周']['周结束']} / 整体{fy['本周']['星数']}星")
            print(f"    本月: {fy['本月']['月柱']}+{fy['本月']['流年']} / {fy['本月']['星数']}星")
            print(f"    本年: {fy['本年']['流年']} / {fy['本年']['星数']}星")
            print(f"    今日健康: {jk['今日']['五行']}气{jk['今日']['状态']} / {jk['今日']['脏腑']}")
            print(f"    节气健康: {jk['节气']['节气']} / {jk['节气']['脏腑']}")
            print(f"    季节健康: {jk['季节']['季节']}季 / {jk['季节']['脏腑']}")
            print(f"    年度健康: {jk['本年']['流年']} / {jk['本年']['脏腑']}")
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"  ❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    print()

print("=" * 60)
print(f"总计: 通过 {passed}/{passed+failed}")
if failed == 0:
    print("🎉 全部通过！skill 可部署")
else:
    print("❌ 部分失败，请检查")
print("=" * 60)

# 输出完整 markdown (Case 1)
print("\n" + "=" * 60)
print("Case 1 完整 markdown 输出（参考）")
print("=" * 60)
report = generate_full_report(test_cases[0]["chart"], target)
md = format_markdown(report)
out_path = _BASE / 'memory' / 'test_fortune_smoke_output.md'
out_path.write_text(md, encoding="utf-8")
print(f"[Markdown saved to: {out_path}]")
print(f"  Size: {len(md)} chars")
