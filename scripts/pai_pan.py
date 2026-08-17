#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四柱八字排盘（零第三方依赖，仅标准库）。

时区一律按北京时间 UTC+8，不用本机本地时区。
节气用太阳视黄经定气（立春=315°），农历用定气定朔
（冬至所在月为十一月，无中气之月为闰月）。

算法锚点（供 QA 对照）
---------------------
1. 日柱：公历儒略日（JDN）→ 六十甲子。
   锚点：1990-05-15 = 庚辰（序号 16：庚=6，辰=4）。
   公式：gz_index = (JDN + 49) % 60。
   日界按早晚子时：23:00 前用当日日柱；23:00 起（含）用次日日柱。

2. 年柱：以该年立春的精确时刻分界，不是正月初一，也不是 2 月 4 日零点。
   年份干支：(year - 4) % 60（1984=甲子）；若时刻 < 该年立春，用 year-1。
   锚点：1990-02-03 10:00 年柱必须是己巳，不是庚午。

3. 月柱：以十二「节」（不是中气）时刻分界：
   立春寅、惊蛰卯、清明辰、立夏巳、芒种午、小暑未、
   立秋申、白露酉、寒露戌、立冬亥、大雪子、小寒丑。
   天干：年上起月。甲己丙作首、乙庚戊为头、丙辛庚上、丁壬壬寅、戊癸甲寅。
   锚点：1990-05-15（立夏后、芒种前）= 辛巳月。

4. 时柱：子 23:00-01:00，丑 01-03，寅 03-05，卯 05-07，辰 07-09，巳 09-11，
   午 11-13，未 13-15，申 15-17，酉 17-19，戌 19-21，亥 21-23。
   五鼠遁元：甲己甲子、乙庚丙子、丙辛戊子、丁壬庚子、戊癸壬子。
   锚点：庚日午时 = 壬午。

5. 十神 / 藏干：与 references/wuxing-tables.md 同一张表，以日干为基准。
   日干那一格十神为「—」。

6. 大运：年干甲丙戊庚壬为阳年；乙丁己辛癸为阴年。
   阳年男/阴年女顺排；阴年男/阳年女逆排。
   从月柱的下一柱（顺）或上一柱（逆）开始，不要把月柱本身当作第一步大运。
   起运年龄 = 出生日到最近「节」的天数 ÷ 3（顺数下一节，逆数上一节）。
   余 1 天 ≈ 4 个月，余 2 天 ≈ 8 个月。起运前用月柱作小运。
   锚点：1990-05-15 男（阳年）必须顺排。

7. 节气时刻：太阳视黄经（Meeus 简式，等价于寿星定气）。
   立春=黄经 315°。精确到小时以上，覆盖 1900–2100。禁止写死「立春大约 2 月 3-5 日」。

8. 农历：节气+朔望。冬至所在月为十一月，无中气之月为闰月。
   朔用 Meeus 定朔（TT），再换北京日期。
   非闰月锚点：1990 农历四月廿一 = 1990-05-15。

9. 神煞：与 references/shensha-table.md 同一张表。只输出命局命中的条目；
   时柱未知则不参与。

真太阳时：默认钟表时间。若给了 --place 且时刻距时辰整点边界 ≤15 分钟，
只加警告「校正后可能跨时辰」，不查经度、不做完整真太阳时。
"""

import argparse
import math
import sys
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BJ = timezone(timedelta(hours=8))
J2000 = 2451545.0
UNIX_JD = 2440587.5  # 1970-01-01 00:00 UTC

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
GAN_WUXING = "木木火火土土金金水水"
ZHI_LIST = list(ZHI)
SHICHEN_SET = set(ZHI_LIST)

# 十二节：黄经、名称、月支下标（寅=2 … 丑=1）
JIE_DEFS = (
    (315, "立春", 2),
    (345, "惊蛰", 3),
    (15, "清明", 4),
    (45, "立夏", 5),
    (75, "芒种", 6),
    (105, "小暑", 7),
    (135, "立秋", 8),
    (165, "白露", 9),
    (195, "寒露", 10),
    (225, "立冬", 11),
    (255, "大雪", 0),
    (285, "小寒", 1),
)
JIE_LONGS = tuple(item[0] for item in JIE_DEFS)
ZHONGQI_LONGS = (0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330)

# 年上起月：寅月天干。甲己丙、乙庚戊、丙辛庚、丁壬壬、戊癸甲
YUE_GAN_YIN = {
    0: 2,
    5: 2,
    1: 4,
    6: 4,
    2: 6,
    7: 6,
    3: 8,
    8: 8,
    4: 0,
    9: 0,
}

# 五鼠遁元：日干 -> 子时天干
ZI_SHI_GAN = {
    0: 0,
    5: 0,
    1: 2,
    6: 2,
    2: 4,
    7: 4,
    3: 6,
    8: 6,
    4: 8,
    9: 8,
}

# 地支藏干：与 references/wuxing-tables.md 同一张表（本气、中气、余气）
CANGGAN = {
    "子": [("癸", "水")],
    "丑": [("己", "土"), ("癸", "水"), ("辛", "金")],
    "寅": [("甲", "木"), ("丙", "火"), ("戊", "土")],
    "卯": [("乙", "木")],
    "辰": [("戊", "土"), ("乙", "木"), ("癸", "水")],
    "巳": [("丙", "火"), ("庚", "金"), ("戊", "土")],
    "午": [("丁", "火"), ("己", "土")],
    "未": [("己", "土"), ("丁", "火"), ("乙", "木")],
    "申": [("庚", "金"), ("壬", "水"), ("戊", "土")],
    "酉": [("辛", "金")],
    "戌": [("戊", "土"), ("辛", "金"), ("丁", "火")],
    "亥": [("壬", "水"), ("甲", "木")],
}

# 十神：rel = (他干五行 - 日干五行) % 5
# 0 同我 / 1 我生 / 2 我克 / 3 克我 / 4 生我
SHISHEN_SAME = ("比肩", "食神", "偏财", "偏官", "偏印")
SHISHEN_DIFF = ("劫财", "伤官", "正财", "正官", "正印")

# 神煞：与 references/shensha-table.md 同一张表
TIANYI = {
    "甲": ("丑", "未"),
    "戊": ("丑", "未"),
    "乙": ("子", "申"),
    "己": ("子", "申"),
    "丙": ("亥", "酉"),
    "丁": ("亥", "酉"),
    "壬": ("卯", "巳"),
    "癸": ("卯", "巳"),
    "庚": ("丑", "未", "寅", "午"),
    "辛": ("寅", "午"),
}
# 天德：("gan", 干) 查天干；("zhi", 支) 查地支
TIANDE = {
    "寅": ("gan", "丁"),
    "卯": ("zhi", "申"),
    "辰": ("gan", "壬"),
    "巳": ("gan", "辛"),
    "午": ("zhi", "亥"),
    "未": ("gan", "甲"),
    "申": ("gan", "癸"),
    "酉": ("zhi", "寅"),
    "戌": ("gan", "丙"),
    "亥": ("gan", "乙"),
    "子": ("gan", "己"),
    "丑": ("gan", "庚"),
}
YUEDE = {
    "寅": "丙",
    "午": "丙",
    "戌": "丙",
    "申": "壬",
    "子": "壬",
    "辰": "壬",
    "亥": "甲",
    "卯": "甲",
    "未": "甲",
    "巳": "庚",
    "酉": "庚",
    "丑": "庚",
}
WENCHANG = {
    "甲": "巳",
    "乙": "午",
    "丙": "申",
    "丁": "酉",
    "戊": "申",
    "己": "酉",
    "庚": "亥",
    "辛": "子",
    "壬": "寅",
    "癸": "卯",
}
XUETANG = {
    "甲": "亥",
    "乙": "午",
    "丙": "寅",
    "丁": "酉",
    "戊": "寅",
    "己": "酉",
    "庚": "巳",
    "辛": "子",
    "壬": "申",
    "癸": "卯",
}
CIGUAN = {
    "甲": "寅",
    "乙": "卯",
    "丙": "巳",
    "丁": "午",
    "戊": "巳",
    "己": "午",
    "庚": "申",
    "辛": "酉",
    "壬": "亥",
    "癸": "子",
}
SANHE = {
    "寅": "火",
    "午": "火",
    "戌": "火",
    "申": "水",
    "子": "水",
    "辰": "水",
    "巳": "金",
    "酉": "金",
    "丑": "金",
    "亥": "木",
    "卯": "木",
    "未": "木",
}
JIANGXING = {"火": "午", "水": "子", "金": "酉", "木": "卯"}
HUAGAI = {"火": "戌", "水": "辰", "金": "丑", "木": "未"}
YIMA = {"火": "申", "水": "寅", "金": "亥", "木": "巳"}
JIESHA = {"水": "巳", "火": "亥", "金": "寅", "木": "申"}
ZAISHA = {"水": "午", "火": "子", "金": "卯", "木": "酉"}
WANGSHEN = {"水": "亥", "火": "巳", "金": "申", "木": "寅"}
TAOHUA = {"火": "卯", "水": "酉", "金": "午", "木": "子"}
GUCHEN = {
    "亥": "寅",
    "子": "寅",
    "丑": "寅",
    "寅": "巳",
    "卯": "巳",
    "辰": "巳",
    "巳": "申",
    "午": "申",
    "未": "申",
    "申": "亥",
    "酉": "亥",
    "戌": "亥",
}
GUASU = {
    "亥": "戌",
    "子": "戌",
    "丑": "戌",
    "寅": "丑",
    "卯": "丑",
    "辰": "丑",
    "巳": "辰",
    "午": "辰",
    "未": "辰",
    "申": "未",
    "酉": "未",
    "戌": "未",
}
JINYU = {
    "甲": "辰",
    "乙": "巳",
    "丙": "未",
    "丁": "申",
    "戊": "未",
    "己": "申",
    "庚": "戌",
    "辛": "亥",
    "壬": "丑",
    "癸": "寅",
}
YANGBLADE = {
    "甲": "卯",
    "乙": "寅",
    "丙": "午",
    "丁": "巳",
    "戊": "午",
    "己": "巳",
    "庚": "酉",
    "辛": "子",
    "壬": "子",
    "癸": "亥",
}
YUANCHEN_FORWARD = {
    "子": "未",
    "丑": "申",
    "寅": "酉",
    "卯": "戌",
    "辰": "亥",
    "巳": "子",
    "午": "丑",
    "未": "寅",
    "申": "卯",
    "酉": "辰",
    "戌": "巳",
    "亥": "午",
}
YUANCHEN_REVERSE = {
    "子": "巳",
    "丑": "午",
    "寅": "未",
    "卯": "申",
    "辰": "酉",
    "巳": "戌",
    "午": "亥",
    "未": "子",
    "申": "丑",
    "酉": "寅",
    "戌": "卯",
    "亥": "辰",
}
XUEREN = {
    "寅": "午",
    "卯": "未",
    "辰": "申",
    "巳": "酉",
    "午": "戌",
    "未": "亥",
    "申": "子",
    "酉": "丑",
    "戌": "寅",
    "亥": "卯",
    "子": "辰",
    "丑": "巳",
}
GAN_LABELS = ("年干", "月干", "日干", "时干")
ZHI_LABELS = ("年支", "月支", "日支", "时支")
MDH_ZHI_LABELS = ("月支", "日支", "时支")

# 时辰中点（仅 shichen、无 clock 时用于节气比较与起运）
SHICHEN_MID = {
    "子": (0, 0),
    "丑": (2, 0),
    "寅": (4, 0),
    "卯": (6, 0),
    "辰": (8, 0),
    "巳": (10, 0),
    "午": (12, 0),
    "未": (14, 0),
    "申": (16, 0),
    "酉": (18, 0),
    "戌": (20, 0),
    "亥": (22, 0),
}

# 时辰整点边界（北京钟表，不含 00:00，因子时跨日在 23:00 / 01:00 换支）
SHICHEN_BOUNDARIES_MIN = (60, 180, 300, 420, 540, 660, 780, 900, 1020, 1140, 1260, 1380)

LUNAR_DAY_NAMES = {
    1: "初一",
    2: "初二",
    3: "初三",
    4: "初四",
    5: "初五",
    6: "初六",
    7: "初七",
    8: "初八",
    9: "初九",
    10: "初十",
    11: "十一",
    12: "十二",
    13: "十三",
    14: "十四",
    15: "十五",
    16: "十六",
    17: "十七",
    18: "十八",
    19: "十九",
    20: "二十",
    21: "廿一",
    22: "廿二",
    23: "廿三",
    24: "廿四",
    25: "廿五",
    26: "廿六",
    27: "廿七",
    28: "廿八",
    29: "廿九",
    30: "三十",
}
LUNAR_MONTH_NAMES = {
    1: "正月",
    2: "二月",
    3: "三月",
    4: "四月",
    5: "五月",
    6: "六月",
    7: "七月",
    8: "八月",
    9: "九月",
    10: "十月",
    11: "十一月",
    12: "十二月",
}


# ---------------------------------------------------------------------------
# 时间 / 儒略日（北京 UTC+8）
# ---------------------------------------------------------------------------

def delta_t_seconds(year):
    """TT−UTC 近似秒，Espenak/Meeus 分段多项式，1900–2100 足够到分钟级。"""
    y = float(year)
    t = y - 2000.0
    if y < 1920:
        t1 = y - 1900.0
        return -2.79 + 1.494119 * t1 - 0.0598939 * t1**2 + 0.0061966 * t1**3 - 0.000197 * t1**4
    if y < 1941:
        t1 = y - 1920.0
        return 21.20 + 0.84493 * t1 - 0.076100 * t1**2 + 0.0020936 * t1**3
    if y < 1961:
        t1 = y - 1950.0
        return 29.07 + 0.407 * t1 - t1**2 / 233.0 + t1**3 / 2547.0
    if y < 1986:
        t1 = y - 1975.0
        return 45.45 + 1.067 * t1 - t1**2 / 260.0 - t1**3 / 718.0
    if y < 2005:
        t1 = y - 2000.0
        return (
            63.86
            + 0.3345 * t1
            - 0.060374 * t1**2
            + 0.0017275 * t1**3
            + 0.000651814 * t1**4
            + 0.00002373599 * t1**5
        )
    if y < 2050:
        return 62.92 + 0.32217 * t + 0.005589 * t * t
    return -20.0 + 32.0 * ((y - 1820.0) / 100.0) ** 2 - 0.5628 * (2150.0 - y)


def jd_from_datetime_utc(dt):
    """datetime（带时区）→ 儒略日（UTC）。"""
    utc = dt.astimezone(timezone.utc)
    unix = (utc - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
    return UNIX_JD + unix / 86400.0


def datetime_utc_from_jd(jd):
    seconds = (jd - UNIX_JD) * 86400.0
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def jd_tt_to_beijing(jd_tt):
    """力学时 JD → 北京时间 datetime。"""
    year = 2000.0 + (jd_tt - J2000) / 365.242189
    utc_jd = jd_tt - delta_t_seconds(year) / 86400.0
    return datetime_utc_from_jd(utc_jd).astimezone(BJ)


def beijing(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=BJ)


def jdn(year, month, day):
    """格里历儒略日数（中午，整数）。用于日柱。"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


# ---------------------------------------------------------------------------
# 太阳视黄经 / 二十四节气
# ---------------------------------------------------------------------------

def sun_apparent_longitude(jd_tt):
    """太阳视黄经（度）。Meeus AA 第 25 章简式，1900–2100 约 0.01°（十余分钟）以内。"""
    T = (jd_tt - J2000) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    mr = math.radians(M)
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(mr)
        + (0.019993 - 0.000101 * T) * math.sin(2.0 * mr)
        + 0.000289 * math.sin(3.0 * mr)
    )
    omega = 125.04 - 1934.136 * T
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    return lam % 360.0


def _lon_delta(actual, target):
    """actual − target，归一到 (−180, 180]。"""
    return (actual - target + 180.0) % 360.0 - 180.0


@lru_cache(maxsize=4096)
def solar_term_jd(year, longitude):
    """给定公历年、目标黄经，返回该年对应定气的 TT 儒略日。

    当年 1 月 1 日太阳黄经约 280°，沿黄道正向走到 target（可跨 360°）。
    立春 = 315°。禁止用「大约 2 月 3–5 日」这种写死日期。
    """
    year = int(year)
    longitude = float(longitude) % 360.0
    delta_lon = (longitude - 280.46646) % 360.0
    jd0 = J2000 + (year - 2000) * 365.242189 + delta_lon / 0.98564736
    lo, hi = jd0 - 8.0, jd0 + 8.0
    for _ in range(52):
        mid = (lo + hi) / 2.0
        if _lon_delta(sun_apparent_longitude(mid), longitude) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def solar_term_beijing(year, longitude):
    return jd_tt_to_beijing(solar_term_jd(year, longitude))


def jie_events_around(year):
    """year-1 … year+1 的十二节，按北京时间排序。每项 (dt, name, zhi_index, lon, year)。"""
    events = []
    for y in (year - 1, year, year + 1):
        for lon, name, zhi_i in JIE_DEFS:
            dt = solar_term_beijing(y, lon)
            events.append((dt, name, zhi_i, lon, y))
    events.sort(key=lambda x: x[0])
    return events


# ---------------------------------------------------------------------------
# 定朔（Meeus 第 49 章）
# ---------------------------------------------------------------------------

def new_moon_jde(k):
    """新月力学时 JDE。k=0 对应 2000-01-06 附近朔。精度约 1–2 分钟。"""
    T = k / 1236.85
    jde = (
        2451550.09766
        + 29.530588861 * k
        + 0.00015437 * T * T
        - 0.000000150 * T * T * T
        + 0.00000000073 * T * T * T * T
    )
    E = 1.0 - 0.002516 * T - 0.0000074 * T * T
    M = math.radians(2.5534 + 29.10535670 * k - 0.0000014 * T * T - 0.00000011 * T * T * T)
    Mp = math.radians(
        201.5643
        + 385.81693528 * k
        + 0.0107582 * T * T
        + 0.00001238 * T * T * T
        - 0.000000058 * T * T * T * T
    )
    F = math.radians(
        160.7108
        + 390.67050284 * k
        - 0.0016118 * T * T
        - 0.00000227 * T * T * T
        + 0.000000011 * T * T * T * T
    )
    omega = math.radians(124.7746 - 1.56375588 * k + 0.0020672 * T * T + 0.00000215 * T * T * T)
    args = (
        Mp,
        M,
        2 * Mp,
        2 * F,
        Mp - M,
        Mp + M,
        2 * M,
        Mp - 2 * F,
        Mp + 2 * F,
        2 * Mp + M,
        3 * Mp,
        M + 2 * F,
        M - 2 * F,
        2 * Mp - M,
        omega,
        Mp + 2 * M,
        2 * Mp - 2 * F,
        3 * M,
        Mp + M - 2 * F,
        2 * Mp + 2 * F,
        Mp + M + 2 * F,
        Mp - M + 2 * F,
        Mp - M - 2 * F,
        3 * Mp + M,
        4 * Mp,
    )
    coef = (
        -0.40720,
        0.17241 * E,
        0.01608,
        0.01039,
        0.00739 * E,
        -0.00514 * E,
        0.00208 * E * E,
        -0.00111,
        -0.00057,
        0.00056 * E,
        -0.00042,
        0.00042 * E,
        0.00038 * E,
        -0.00024 * E,
        -0.00017,
        -0.00007,
        0.00004,
        0.00004,
        0.00003,
        0.00003,
        -0.00003,
        0.00003,
        -0.00002,
        -0.00002,
        0.00002,
    )
    jde += sum(c * math.sin(a) for c, a in zip(coef, args))
    A = (
        299.77 + 0.107408 * k - 0.009173 * T * T,
        251.88 + 0.016321 * k,
        251.83 + 26.651886 * k,
        349.42 + 36.412478 * k,
        84.66 + 18.206239 * k,
        141.74 + 53.303771 * k,
        207.14 + 2.453732 * k,
        154.84 + 7.306860 * k,
        34.52 + 27.261239 * k,
        207.19 + 0.121824 * k,
        291.34 + 1.844379 * k,
        161.72 + 24.198154 * k,
        239.56 + 25.513099 * k,
        331.55 + 3.592518 * k,
    )
    Ac = (325, 165, 164, 126, 110, 62, 60, 56, 47, 42, 40, 37, 35, 23)
    jde += sum(c * 1e-6 * math.sin(math.radians(a)) for c, a in zip(Ac, A))
    return jde


def _k_near(jd):
    return int(round((jd - 2451550.09766) / 29.530588861))


def last_new_moon_k_on_or_before(jd_tt):
    k = _k_near(jd_tt)
    while new_moon_jde(k) > jd_tt:
        k -= 1
    while new_moon_jde(k + 1) <= jd_tt:
        k += 1
    return k


# ---------------------------------------------------------------------------
# 农历（冬至十一月 + 无中气置闰）
# ---------------------------------------------------------------------------

def _zhongqi_jds(year):
    out = []
    for y in (year - 1, year, year + 1):
        for lon in ZHONGQI_LONGS:
            out.append(solar_term_jd(y, lon))
    return out


@lru_cache(maxsize=256)
def lunar_months_between_dongzhi(dongzhi_year):
    """从「dongzhi_year 的冬至所在十一月」起到下一年冬至月之前的各农历月。

    返回 tuple of dict:
      year, month, leap, start (date), days, shuo_jd
    1990 年有闰五月；1990-04-21（非闰）= 1990-05-15。
    """
    y = int(dongzhi_year)
    dz0 = solar_term_jd(y, 270)
    dz1 = solar_term_jd(y + 1, 270)
    k0 = last_new_moon_k_on_or_before(dz0)
    k1 = last_new_moon_k_on_or_before(dz1)
    moons = [new_moon_jde(k) for k in range(k0, k1 + 1)]
    n = len(moons) - 1
    zhong = _zhongqi_jds(y)
    leap_index = None
    if n == 13:
        for i in range(n):
            has = False
            for z in zhong:
                if moons[i] <= z < moons[i + 1]:
                    has = True
                    break
            if not has:
                leap_index = i
                break
    months = []
    month_num = 11
    lunar_year = y
    for i in range(n):
        is_leap = leap_index is not None and i == leap_index
        if i > 0 and not is_leap:
            month_num += 1
            if month_num == 13:
                month_num = 1
                lunar_year = y + 1
        start_d = jd_tt_to_beijing(moons[i]).date()
        next_d = jd_tt_to_beijing(moons[i + 1]).date()
        days = (next_d - start_d).days
        months.append(
            {
                "year": lunar_year,
                "month": month_num,
                "leap": is_leap,
                "start": start_d,
                "days": days,
                "shuo_jd": moons[i],
            }
        )
    return tuple(months)


def lunar_months_covering_solar_year(solar_year):
    """覆盖该公历年的农历月（含前后冬至段，去重）。"""
    a = lunar_months_between_dongzhi(solar_year - 1)
    b = lunar_months_between_dongzhi(solar_year)
    seen = set()
    out = []
    for m in a + b:
        key = (m["start"], m["year"], m["month"], m["leap"])
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    out.sort(key=lambda x: x["start"])
    return out


def solar_to_lunar(y, m, d):
    """公历日 → (农历年, 月, 日, 是否闰月)。"""
    target = date(y, m, d)
    months = lunar_months_covering_solar_year(y)
    # 跨年：1 月可能落在上一段十二月，12 月落在下一年冬至段
    if y - 1 >= 1890:
        extra = lunar_months_between_dongzhi(y - 2)
        months = list(extra) + list(months)
    for info in months:
        start = info["start"]
        end = start + timedelta(days=info["days"])
        if start <= target < end:
            return info["year"], info["month"], (target - start).days + 1, info["leap"]
    raise ValueError("无法把 %04d-%02d-%02d 换成农历（超出推算范围）" % (y, m, d))


def lunar_to_solar(ly, lm, ld, leap=False):
    """农历日 → 公历 date。闰月必须 leap=True。"""
    # 正月在「冬至(ly-1) → 冬至(ly)」段；冬月、腊月在下一段
    months = list(lunar_months_between_dongzhi(ly - 1)) + list(lunar_months_between_dongzhi(ly))
    found = None
    for info in months:
        if info["year"] == ly and info["month"] == lm and bool(info["leap"]) == bool(leap):
            found = info
            break
    if found is None:
        if leap:
            raise ValueError("农历 %d年没有闰%s" % (ly, LUNAR_MONTH_NAMES.get(lm, str(lm) + "月")))
        raise ValueError("找不到农历 %d年%s" % (ly, LUNAR_MONTH_NAMES.get(lm, str(lm) + "月")))
    if ld < 1 or ld > found["days"]:
        raise ValueError(
            "农历 %d年%s%s只有 %d 天"
            % (
                ly,
                "闰" if leap else "",
                LUNAR_MONTH_NAMES.get(lm, str(lm) + "月"),
                found["days"],
            )
        )
    return found["start"] + timedelta(days=ld - 1)


def format_lunar(ly, lm, ld, leap):
    return "%d年%s%s%s" % (
        ly,
        "闰" if leap else "",
        LUNAR_MONTH_NAMES.get(lm, str(lm) + "月"),
        LUNAR_DAY_NAMES.get(ld, str(ld)),
    )


# ---------------------------------------------------------------------------
# 干支 / 十神 / 藏干
# ---------------------------------------------------------------------------

def gz_from_index(idx):
    idx = int(idx) % 60
    return GAN[idx % 10], ZHI[idx % 12]


def year_gz_index(year):
    """立春后的年干支序号。1984=甲子=0。"""
    return (int(year) - 4) % 60


def day_gz_index(year, month, day):
    """日柱序号。锚点 1990-05-15 = 16 庚辰。"""
    return (jdn(year, month, day) + 49) % 60


def shishen_of(day_gan, other_gan):
    if other_gan is None:
        return "—"
    rel = (other_gan // 2 - day_gan // 2) % 5
    if (day_gan % 2) == (other_gan % 2):
        return SHISHEN_SAME[rel]
    return SHISHEN_DIFF[rel]


def format_canggan(zhi):
    parts = CANGGAN.get(zhi, [])
    return "、".join("%s%s" % (g, wx) for g, wx in parts)


def _shensha_positions(needles, values, labels):
    if isinstance(needles, str):
        needles = (needles,)
    need = set(needles)
    out = []
    for val, lab in zip(values, labels):
        if val is not None and val in need:
            out.append(lab)
    return out


def _sanhe_needles(year_zhi, day_zhi, table):
    return {table[SANHE[year_zhi]], table[SANHE[day_zhi]]}


def kongwang_zhi(day_gan, day_zhi):
    """日柱所在旬的两个空亡地支。甲子旬戌亥，余旬依次前移。"""
    start = (ZHI.index(day_zhi) - GAN.index(day_gan)) % 12
    return ZHI[(start - 2) % 12], ZHI[(start - 1) % 12]


def compute_shensha(
    year_gan,
    year_zhi,
    month_gan,
    month_zhi,
    day_gan,
    day_zhi,
    hour_gan,
    hour_zhi,
    sex,
):
    """命中的神煞行。口径同 references/shensha-table.md；时柱未知则 hour_* 为 None。"""
    gans = (year_gan, month_gan, day_gan, hour_gan)
    zhis = (year_zhi, month_zhi, day_zhi, hour_zhi)
    mdh_zhis = (month_zhi, day_zhi, hour_zhi)
    lines = []

    def add(name, positions, method):
        if positions:
            lines.append("- %s — 见于%s — %s" % (name, "、".join(positions), method))

    tianyi_need = set(TIANYI[year_gan])
    tianyi_need.update(TIANYI[day_gan])
    add("天乙贵人", _shensha_positions(tianyi_need, zhis, ZHI_LABELS), "年干/日干查地支")

    td_kind, td_word = TIANDE[month_zhi]
    if td_kind == "gan":
        add("天德", _shensha_positions(td_word, gans, GAN_LABELS), "月支查天干")
    else:
        add("天德", _shensha_positions(td_word, zhis, ZHI_LABELS), "月支查地支")

    add("月德", _shensha_positions(YUEDE[month_zhi], gans, GAN_LABELS), "月支三合")

    wenchang_need = {WENCHANG[year_gan], WENCHANG[day_gan]}
    add("文昌", _shensha_positions(wenchang_need, zhis, ZHI_LABELS), "年干/日干查地支")
    add("学堂", _shensha_positions(XUETANG[day_gan], zhis, ZHI_LABELS), "日干长生")
    add("词馆", _shensha_positions(CIGUAN[day_gan], zhis, ZHI_LABELS), "日干临官")

    add(
        "将星",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, JIANGXING), zhis, ZHI_LABELS),
        "年支/日支三合",
    )
    add(
        "华盖",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, HUAGAI), zhis, ZHI_LABELS),
        "年支/日支",
    )
    add(
        "驿马",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, YIMA), zhis, ZHI_LABELS),
        "年支/日支",
    )

    tianyi_prev = ZHI[(ZHI.index(month_zhi) - 1) % 12]
    add("天医", _shensha_positions(tianyi_prev, zhis, ZHI_LABELS), "月支前一位")
    add("禄神", _shensha_positions(CIGUAN[day_gan], zhis, ZHI_LABELS), "日干")
    add("金舆", _shensha_positions(JINYU[day_gan], zhis, ZHI_LABELS), "日干")
    add("羊刃", _shensha_positions(YANGBLADE[day_gan], zhis, ZHI_LABELS), "日干")
    add(
        "劫煞",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, JIESHA), zhis, ZHI_LABELS),
        "年支/日支",
    )
    add(
        "灾煞",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, ZAISHA), zhis, ZHI_LABELS),
        "年支/日支",
    )
    add(
        "亡神",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, WANGSHEN), zhis, ZHI_LABELS),
        "年支/日支",
    )
    add(
        "桃花/咸池",
        _shensha_positions(_sanhe_needles(year_zhi, day_zhi, TAOHUA), zhis, ZHI_LABELS),
        "年支/日支",
    )
    add("孤辰", _shensha_positions(GUCHEN[year_zhi], zhis, ZHI_LABELS), "年支")
    add("寡宿", _shensha_positions(GUASU[year_zhi], zhis, ZHI_LABELS), "年支")
    add("空亡/旬空", _shensha_positions(kongwang_zhi(day_gan, day_zhi), zhis, ZHI_LABELS), "日柱旬空")

    yang_year = GAN.index(year_gan) % 2 == 0
    yuan_map = YUANCHEN_FORWARD if (yang_year == (sex == "男")) else YUANCHEN_REVERSE
    add("元辰", _shensha_positions(yuan_map[year_zhi], mdh_zhis, MDH_ZHI_LABELS), "年支阴阳男女")
    add("血刃", _shensha_positions(XUEREN[month_zhi], zhis, ZHI_LABELS), "月支")
    return lines


def hour_to_shichen(hour, minute):
    """钟点 → 时支。23:00–01:00 子，其后每两小时一支。"""
    total = hour * 60 + minute
    if total >= 23 * 60 or total < 60:
        return "子"
    # 01:00 起：丑=1 … 亥=11
    idx = ((hour + 1) // 2) % 12
    return ZHI[idx]


def near_shichen_boundary(hour, minute):
    total = hour * 60 + minute
    for b in SHICHEN_BOUNDARIES_MIN:
        if abs(total - b) <= 15:
            return True
    return False


# ---------------------------------------------------------------------------
# 排盘
# ---------------------------------------------------------------------------

def resolve_year_pillar(birth_dt):
    """立春时刻分年。1990-02-03 10:00 → 己巳。"""
    cal_year = birth_dt.year
    lichun = solar_term_beijing(cal_year, 315)
    year_num = cal_year if birth_dt >= lichun else cal_year - 1
    gan, zhi = gz_from_index(year_gz_index(year_num))
    return year_num, gan, zhi, lichun


def resolve_month_pillar(birth_dt, year_gan):
    """十二节分月 + 年上起月。1990-05-15 → 辛巳。"""
    events = jie_events_around(birth_dt.year)
    current = None
    next_jie = None
    prev_jie = None
    for i, ev in enumerate(events):
        if ev[0] <= birth_dt:
            current = ev
        elif next_jie is None:
            next_jie = ev
            if i >= 1:
                prev_jie = events[i - 1]
            break
    if current is None:
        raise ValueError("找不到出生时刻之前的节气")
    if prev_jie is None:
        # birth 落在列表最后一节之后
        prev_jie = current
        # next 取更后面一年
        later = jie_events_around(birth_dt.year + 1)
        for ev in later:
            if ev[0] > birth_dt:
                next_jie = ev
                break
    _dt, name, zhi_i, lon, _y = current
    yue_zhi = ZHI[zhi_i]
    # 寅=2 对应年上起月的第 0 步
    step = (zhi_i - 2) % 12
    yue_gan = GAN[(YUE_GAN_YIN[year_gan] + step) % 10]
    return yue_gan, yue_zhi, name, lon, prev_jie[0], next_jie[0] if next_jie else None


def resolve_day_pillar(solar_date, hour, minute):
    """早晚子时日界。返回 (gan, zhi, index, used_date, zishi_label)。"""
    used = date(solar_date.year, solar_date.month, solar_date.day)
    zishi = "无"
    if hour is not None:
        if hour >= 23:
            used = used + timedelta(days=1)
            zishi = "夜子时"
        elif hour == 0:
            zishi = "早子时"
    idx = day_gz_index(used.year, used.month, used.day)
    gan, zhi = gz_from_index(idx)
    return gan, zhi, idx, used, zishi


def resolve_hour_pillar(day_gan, shichen):
    if not shichen:
        return None, None
    zhi_i = ZHI.index(shichen)
    gan_i = (ZI_SHI_GAN[day_gan] + zhi_i) % 10
    return GAN[gan_i], ZHI[zhi_i]


def qiyun_from_days(days):
    """天数 ÷ 3 = 岁；余 1 天≈4 个月，余 2 天≈8 个月。不足一天按比例折月。"""
    days = abs(float(days))
    whole = int(days)
    frac = days - whole
    years, rem = divmod(whole, 3)
    months = rem * 4 + int(round(frac * 4))
    if months >= 12:
        years += months // 12
        months = months % 12
    return years, months


def build_dayun(month_gan, month_zhi, forward, qiyun_years, qiyun_months, steps=8):
    """从月柱下一柱（顺）或上一柱（逆）起排。月柱本身是起运前小运。"""
    gi = GAN.index(month_gan)
    zi = ZHI.index(month_zhi)
    delta = 1 if forward else -1
    rows = []
    start_age = qiyun_years
    if qiyun_years > 0 or qiyun_months > 0:
        if qiyun_months == 0:
            pre_end = "%d岁" % qiyun_years
        else:
            pre_end = "%d岁%d个月" % (qiyun_years, qiyun_months)
        rows.append(("起运前", "0岁-" + pre_end, month_gan + month_zhi + "（小运）"))
    for n in range(1, steps + 1):
        gi = (gi + delta) % 10
        zi = (zi + delta) % 12
        a0 = start_age + (n - 1) * 10
        a1 = a0 + 9
        rows.append((str(n), "%d-%d岁" % (a0, a1), GAN[gi] + ZHI[zi]))
    return rows


def liunian_gz(year):
    g, z = gz_from_index(year_gz_index(year))
    return g + z


def compute(
    solar_date,
    hour=None,
    minute=None,
    shichen=None,
    sex="男",
    place=None,
    deceased_year=None,
    lunar_display=None,
    now=None,
):
    """核心排盘。solar_date 为公历 date；hour/minute 为北京钟表，可空。"""
    warnings = []
    clock_known = hour is not None
    shichen_known = bool(shichen)

    if clock_known:
        shichen = hour_to_shichen(hour, minute)
    elif shichen_known:
        hour, minute = SHICHEN_MID[shichen]
    else:
        hour, minute = 12, 0
        warnings.append("时辰未知")

    birth_dt = beijing(solar_date.year, solar_date.month, solar_date.day, hour, minute)

    year_num, year_gan, year_zhi, lichun = resolve_year_pillar(birth_dt)
    month_gan, month_zhi, jie_name, jie_lon, prev_jie_dt, next_jie_dt = resolve_month_pillar(
        birth_dt, GAN.index(year_gan)
    )

    if clock_known:
        d_gan, d_zhi, d_idx, day_used, zishi = resolve_day_pillar(solar_date, hour, minute)
    elif shichen_known and shichen == "子":
        d_gan, d_zhi, d_idx, day_used, zishi = resolve_day_pillar(solar_date, 0, 0)
        warnings.append("未提供具体时刻，子时按早子时（当日日柱）处理")
    else:
        d_gan, d_zhi, d_idx, day_used, zishi = resolve_day_pillar(solar_date, None, None)

    if clock_known or shichen_known:
        h_gan, h_zhi = resolve_hour_pillar(GAN.index(d_gan), shichen)
        hour_unknown = False
    else:
        h_gan, h_zhi = None, None
        hour_unknown = True
        zishi = "无"

    day_gan_i = GAN.index(d_gan)
    pillars = {
        "year": (year_gan, year_zhi, shishen_of(day_gan_i, GAN.index(year_gan)), format_canggan(year_zhi)),
        "month": (month_gan, month_zhi, shishen_of(day_gan_i, GAN.index(month_gan)), format_canggan(month_zhi)),
        "day": (d_gan, d_zhi, "—", format_canggan(d_zhi)),
        "hour": (
            "未知" if hour_unknown else h_gan,
            "未知" if hour_unknown else h_zhi,
            "未知" if hour_unknown else shishen_of(day_gan_i, GAN.index(h_gan)),
            "未知" if hour_unknown else format_canggan(h_zhi),
        ),
    }

    year_gan_i = GAN.index(year_gan)
    yang_year = year_gan_i % 2 == 0
    if sex == "男":
        forward = yang_year
    else:
        forward = not yang_year
    # 1990-05-15 男（庚午阳年）必须顺排

    if forward:
        jie_for_qiyun = next_jie_dt
    else:
        jie_for_qiyun = prev_jie_dt
    if jie_for_qiyun is None:
        raise ValueError("无法定位起运所用的节")
    delta_sec = (jie_for_qiyun - birth_dt).total_seconds()
    qiyun_days = abs(delta_sec) / 86400.0
    qy, qm = qiyun_from_days(qiyun_days)
    dayun_rows = build_dayun(month_gan, month_zhi, forward, qy, qm)

    # 节气交界 / 立春前后：距节或立春 24 小时内
    if next_jie_dt is not None and abs((birth_dt - next_jie_dt).total_seconds()) <= 86400:
        warnings.append("节气交界")
    if abs((birth_dt - prev_jie_dt).total_seconds()) <= 86400:
        if "节气交界" not in warnings:
            warnings.append("节气交界")
    if abs((birth_dt - lichun).total_seconds()) <= 86400:
        warnings.append("立春前后")
    else:
        # 邻近上一年或下一年立春
        for y in (birth_dt.year - 1, birth_dt.year + 1):
            lc = solar_term_beijing(y, 315)
            if abs((birth_dt - lc).total_seconds()) <= 86400:
                warnings.append("立春前后")
                break

    if place and clock_known and near_shichen_boundary(hour, minute):
        warnings.append("校正后可能跨时辰")

    if now is None:
        now = datetime.now(BJ)
    current_year = now.year
    if deceased_year is not None:
        end_year = int(deceased_year)
        show_current_year = end_year
    else:
        end_year = current_year
        show_current_year = current_year
    birth_year = solar_date.year
    if end_year < birth_year:
        end_year = birth_year

    liunian_years = list(range(birth_year, end_year + 1))

    if lunar_display is None:
        try:
            ly, lm, ld, leap = solar_to_lunar(solar_date.year, solar_date.month, solar_date.day)
            lunar_display = format_lunar(ly, lm, ld, leap)
        except ValueError as exc:
            lunar_display = "未知"
            warnings.append(str(exc))

    if clock_known:
        solar_text = "%04d-%02d-%02d %02d:%02d" % (
            solar_date.year,
            solar_date.month,
            solar_date.day,
            hour,
            minute,
        )
        shichen_text = "%s / %02d:%02d" % (shichen, hour, minute)
    elif shichen_known:
        solar_text = "%04d-%02d-%02d" % (solar_date.year, solar_date.month, solar_date.day)
        shichen_text = shichen
    else:
        solar_text = "%04d-%02d-%02d" % (solar_date.year, solar_date.month, solar_date.day)
        shichen_text = "未知"

    if qm:
        qiyun_text = "%d岁%d个月" % (qy, qm)
    else:
        qiyun_text = "%d岁" % qy

    shensha_lines = compute_shensha(
        year_gan,
        year_zhi,
        month_gan,
        month_zhi,
        d_gan,
        d_zhi,
        h_gan,
        h_zhi,
        sex,
    )

    return {
        "solar_text": solar_text,
        "lunar_text": lunar_display,
        "shichen_text": shichen_text,
        "sex": sex,
        "place": place,
        "zishi": zishi,
        "pillars": pillars,
        "forward": forward,
        "qiyun_text": qiyun_text,
        "qiyun_years": qy,
        "qiyun_months": qm,
        "dayun_rows": dayun_rows,
        "liunian_years": liunian_years,
        "current_year": show_current_year,
        "current_gz": liunian_gz(show_current_year),
        "warnings": warnings,
        "hour_unknown": hour_unknown,
        "year_num": year_num,
        "jie_name": jie_name,
        "birth_dt": birth_dt,
        "shensha_lines": shensha_lines,
    }


def format_report(result):
    p = result["pillars"]
    lines = []
    lines.append("## 输入")
    lines.append("- 阳历：%s" % result["solar_text"])
    lines.append("- 农历：%s" % result["lunar_text"])
    lines.append("- 时辰：%s" % result["shichen_text"])
    lines.append("- 性别：%s" % result["sex"])
    if result["place"]:
        lines.append("- 出生地：%s" % result["place"])
    lines.append("- 子时：%s" % result["zishi"])
    lines.append("")
    lines.append("## 四柱")
    lines.append("| | 年柱 | 月柱 | 日柱 | 时柱 |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        "| 天干 | %s | %s | %s | %s |" % (p["year"][0], p["month"][0], p["day"][0], p["hour"][0])
    )
    lines.append(
        "| 地支 | %s | %s | %s | %s |" % (p["year"][1], p["month"][1], p["day"][1], p["hour"][1])
    )
    lines.append(
        "| 十神 | %s | %s | %s | %s |" % (p["year"][2], p["month"][2], p["day"][2], p["hour"][2])
    )
    lines.append(
        "| 藏干 | %s | %s | %s | %s |" % (p["year"][3], p["month"][3], p["day"][3], p["hour"][3])
    )
    lines.append("")
    lines.append("## 大运")
    lines.append("- 方向：%s" % ("顺排" if result["forward"] else "逆排"))
    lines.append("- 起运：%s" % result["qiyun_text"])
    lines.append("| 大运序 | 年龄范围 | 干支 |")
    lines.append("|---|---|---|")
    for seq, ages, gz in result["dayun_rows"]:
        lines.append("| %s | %s | %s |" % (seq, ages, gz))
    lines.append("")
    lines.append("## 流年")
    lines.append("- 当前：%d年%s" % (result["current_year"], result["current_gz"]))
    for y in result["liunian_years"]:
        lines.append("- %d年%s" % (y, liunian_gz(y)))
    lines.append("")
    lines.append("## 神煞")
    lines.extend(result["shensha_lines"])
    lines.append("")
    lines.append("## 警告")
    if result["warnings"]:
        # 去重且保持顺序
        seen = set()
        for w in result["warnings"]:
            if w in seen:
                continue
            seen.add(w)
            lines.append("- %s" % w)
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_iso_date(text, flag):
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return date(y, m, d)
    except ValueError:
        raise argparse.ArgumentTypeError("%s 需要 YYYY-MM-DD，收到 %r" % (flag, text))


def parse_hour(text):
    try:
        hh, mm = text.split(":")
        h, m = int(hh), int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except ValueError:
        raise argparse.ArgumentTypeError("--hour 需要 HH:MM，收到 %r" % text)


def build_parser():
    p = argparse.ArgumentParser(description="四柱八字排盘（北京时间，无第三方依赖）")
    p.add_argument("--solar", help="阳历 YYYY-MM-DD")
    p.add_argument("--lunar", help="农历 YYYY-MM-DD（年-月-日数字）")
    p.add_argument("--leap", action="store_true", help="农历闰月")
    p.add_argument("--hour", help="出生钟点 HH:MM（北京时间），与 --shichen 互斥")
    p.add_argument("--shichen", choices=ZHI_LIST, help="时辰地支")
    p.add_argument("--sex", required=True, choices=("男", "女"), help="性别（必填）")
    p.add_argument("--place", help="出生地（只展示；近时辰边界时警告）")
    p.add_argument("--deceased-year", type=int, dest="deceased_year", help="已故年份，流年只列到该年")
    return p


def run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.solar and not args.lunar:
        parser.error("至少提供 --solar 或 --lunar")
    if args.hour and args.shichen:
        parser.error("--hour 与 --shichen 互斥")
    if args.leap and not args.lunar:
        parser.error("--leap 只能与 --lunar 同时使用")

    hour = minute = None
    if args.hour:
        hour, minute = parse_hour(args.hour)

    solar_date = None
    lunar_display = None
    if args.solar:
        solar_date = parse_iso_date(args.solar, "--solar")
    if args.lunar:
        lunar_date = parse_iso_date(args.lunar, "--lunar")
        try:
            converted = lunar_to_solar(lunar_date.year, lunar_date.month, lunar_date.day, leap=args.leap)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        lunar_display = format_lunar(lunar_date.year, lunar_date.month, lunar_date.day, args.leap)
        if solar_date is None:
            solar_date = converted
        # 两个都给：以阳历为准，农历仅展示（用用户给的农历字串）

    try:
        result = compute(
            solar_date=solar_date,
            hour=hour,
            minute=minute,
            shichen=args.shichen,
            sex=args.sex,
            place=args.place,
            deceased_year=args.deceased_year,
            lunar_display=lunar_display if args.lunar and args.solar else None,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # 仅农历输入时，展示用户农历；同时用换算出的阳历
    if args.lunar and not args.solar:
        result["lunar_text"] = lunar_display

    report = format_report(result)
    sys.stdout.write(report)
    if not report.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
