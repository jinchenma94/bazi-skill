#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pai_pan.py 回归：用 stdout 断言黄金用例与日界/大运/农历/流年。"""

import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "pai_pan.py")
PY = sys.executable


def run_pai(*args):
    proc = subprocess.run(
        [PY, SCRIPT] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def section(stdout, title):
    """截取 '## title' 到下一个 '##'（不含）。"""
    marker = "## " + title
    start = stdout.find(marker)
    if start < 0:
        return ""
    rest = stdout[start + len(marker) :]
    nxt = rest.find("\n## ")
    if nxt < 0:
        return rest
    return rest[:nxt]


def table_row(stdout, cell0):
    for line in stdout.splitlines():
        if line.startswith("| " + cell0 + " |"):
            return [p.strip() for p in line.strip().strip("|").split("|")]
    return []


def pillars(stdout):
    gan = table_row(stdout, "天干")
    zhi = table_row(stdout, "地支")
    # gan/zhi: ['天干', 年, 月, 日, 时]
    return {
        "year": (gan[1] if gan else "") + (zhi[1] if zhi else ""),
        "month": (gan[2] if gan else "") + (zhi[2] if zhi else ""),
        "day": (gan[3] if gan else "") + (zhi[3] if zhi else ""),
        "hour": (gan[4] if gan else "") + (zhi[4] if zhi else ""),
        "gan": gan[1:] if gan else [],
        "zhi": zhi[1:] if zhi else [],
    }


def field(stdout, name):
    m = re.search(r"^- %s：(.+)$" % re.escape(name), stdout, re.M)
    return m.group(1).strip() if m else ""


class PaiPanTests(unittest.TestCase):
    def test_golden_1990_wushi_male(self):
        """1990-05-15 午时男：庚午 / 辛巳 / 庚辰 / 壬午，顺排，神煞已计算。"""
        code, out, err = run_pai("--solar", "1990-05-15", "--shichen", "午", "--sex", "男")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["year"], "庚午")
        self.assertEqual(p["month"], "辛巳")
        self.assertEqual(p["day"], "庚辰")
        self.assertEqual(p["hour"], "壬午")
        self.assertIn("方向：顺排", out)
        shensha = section(out, "神煞").strip()
        self.assertNotEqual(shensha, "未计算")
        self.assertTrue(shensha)
        self.assertIn("天乙贵人", shensha)
        self.assertNotIn("Traceback", out)
        self.assertNotIn("Traceback", err)

    def test_before_lichun_year_is_jisi(self):
        """1990-02-03 10:00 在立春前，年柱己巳，不是庚午。"""
        code, out, err = run_pai("--solar", "1990-02-03", "--hour", "10:00", "--sex", "男")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["year"], "己巳")
        self.assertNotEqual(p["year"], "庚午")

    def test_late_zi_uses_next_day_pillar(self):
        """23:30 夜子时：日柱用次日辛巳，时支子。"""
        code, out, err = run_pai("--solar", "1990-05-15", "--hour", "23:30", "--sex", "男")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["day"], "辛巳")
        self.assertEqual(p["zhi"][3], "子")
        self.assertEqual(field(out, "子时"), "夜子时")

    def test_early_zi_keeps_same_day_pillar(self):
        """00:30 早子时：日柱仍庚辰，时支子。"""
        code, out, err = run_pai("--solar", "1990-05-15", "--hour", "00:30", "--sex", "男")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["day"], "庚辰")
        self.assertEqual(p["zhi"][3], "子")
        self.assertEqual(field(out, "子时"), "早子时")

    def test_yin_year_male_dayun_reverse(self):
        """1991-06-15 辛未阴年男，大运逆排。"""
        code, out, err = run_pai("--solar", "1991-06-15", "--shichen", "午", "--sex", "男")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["year"], "辛未")
        self.assertIn("方向：逆排", out)

    def test_yang_year_female_dayun_reverse(self):
        """1990-05-15 阳年女，大运逆排。"""
        code, out, err = run_pai("--solar", "1990-05-15", "--shichen", "午", "--sex", "女")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["year"], "庚午")
        self.assertIn("方向：逆排", out)

    def test_unknown_hour_keeps_ymd(self):
        """无 hour/shichen：时柱未知，年月日柱完整。"""
        code, out, err = run_pai("--solar", "1990-05-15", "--sex", "男")
        self.assertEqual(code, 0, err)
        p = pillars(out)
        self.assertEqual(p["year"], "庚午")
        self.assertEqual(p["month"], "辛巳")
        self.assertEqual(p["day"], "庚辰")
        self.assertEqual(p["gan"][3], "未知")
        self.assertEqual(p["zhi"][3], "未知")
        self.assertEqual(field(out, "时辰"), "未知")
        self.assertEqual(field(out, "子时"), "无")
        self.assertIn("时辰未知", section(out, "警告"))

    def test_lunar_non_leap_matches_solar(self):
        """农历 1990-04-21（非闰四月廿一）与阳历 1990-05-15 四柱一致。"""
        code_l, out_l, err_l = run_pai("--lunar", "1990-04-21", "--shichen", "午", "--sex", "男")
        code_s, out_s, err_s = run_pai("--solar", "1990-05-15", "--shichen", "午", "--sex", "男")
        self.assertEqual(code_l, 0, err_l)
        self.assertEqual(code_s, 0, err_s)
        self.assertEqual(pillars(out_l), pillars(out_s))

    def test_deceased_year_stops_liunian(self):
        """--deceased-year 2010：流年不出现 2011 及更晚。"""
        code, out, err = run_pai(
            "--solar",
            "1990-05-15",
            "--hour",
            "12:00",
            "--sex",
            "男",
            "--deceased-year",
            "2010",
        )
        self.assertEqual(code, 0, err)
        liunian = section(out, "流年")
        self.assertIn("2010", liunian)
        self.assertNotIn("2011", liunian)
        self.assertNotIn("2012", liunian)
        self.assertNotIn("2020", liunian)
        self.assertNotIn("2026", liunian)


class ShenshaTests(unittest.TestCase):
    def test_golden_shensha_hits_and_misses(self):
        """1990-05-15 午时男：有天乙贵人、将星；地支无申无卯，无驿马、桃花。"""
        code, out, err = run_pai("--solar", "1990-05-15", "--shichen", "午", "--sex", "男")
        self.assertEqual(code, 0, err)
        shensha = section(out, "神煞")
        self.assertNotEqual(shensha.strip(), "未计算")
        self.assertIn("天乙贵人", shensha)
        self.assertIn("将星", shensha)
        self.assertNotIn("驿马", shensha)
        self.assertNotIn("桃花", shensha)

    def test_shensha_table_driven(self):
        """日干甲见丑为天乙；日柱甲子旬空戌亥。"""
        sys.path.insert(0, HERE)
        import pai_pan

        cases = (
            {
                "name": "日干甲+地支丑→天乙",
                "args": ("乙", "亥", "戊", "丑", "甲", "寅", None, None, "男"),
                "has": ("天乙贵人",),
            },
            {
                "name": "日柱甲子→空亡戌亥",
                "args": ("甲", "戌", "乙", "亥", "甲", "子", None, None, "男"),
                "has": ("空亡",),
            },
        )
        for case in cases:
            with self.subTest(case["name"]):
                text = "\n".join(pai_pan.compute_shensha(*case["args"]))
                for name in case["has"]:
                    self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
