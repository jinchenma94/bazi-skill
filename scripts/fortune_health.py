# -*- coding: utf-8 -*-
"""
bazi-fortune 运势 + 健康计算引擎（确定性算法，不依赖 LLM）

输入: bazi_chart (dict) + current_date (date)
输出: 8 维度结构化数据 (dict) + 可直接渲染的 markdown 文本

支持:
  运势: 今日 / 本周 / 本月 / 本年
  健康: 今日 / 当前节气 / 当前季节 / 本年

算法核心:
  1. 日主强弱判断（统计四柱五行力量）
  2. 喜忌神判定（身旺喜泄耗克，忌生扶；身弱反之）
  3. 各时间干支打分（-3..+3 整数）
  4. 线性映射 1-5 星（-3→1, 0→3, +3→5）
  5. 健康：五行 → 脏腑 映射

版本: v1.0 (2026-06-29)
"""

from datetime import date, timedelta

# === 基础常量 ===

TG = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DZ = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

TG_WUXING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}

TG_YINYANG = {
    "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
    "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴",
}

DZ_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 地支藏干（本气 / 中气 / 余气，权重 0.6 / 0.3 / 0.1）
DZ_CANGAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

# 五行生克
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 24 节气（按月份分界，简化版日期）
# 实际节气日期 ±1-2 天偏差，不影响五季判断
JIEQI_TABLE = [
    # (节气名, 五行, 起始月日)
    ("小寒", "水", 1, 5), ("大寒", "水", 1, 20),
    ("立春", "木", 2, 4), ("雨水", "木", 2, 19),
    ("惊蛰", "木", 3, 5), ("春分", "木", 3, 20),
    ("清明", "木", 4, 4), ("谷雨", "木", 4, 20),
    ("立夏", "火", 5, 5), ("小满", "火", 5, 20),
    ("芒种", "火", 6, 5), ("夏至", "火", 6, 21),
    ("小暑", "火", 7, 7), ("大暑", "火", 7, 22),
    ("立秋", "金", 8, 7), ("处暑", "金", 8, 23),
    ("白露", "金", 9, 7), ("秋分", "金", 9, 22),
    ("寒露", "金", 10, 8), ("霜降", "金", 10, 23),
    ("立冬", "水", 11, 7), ("小雪", "水", 11, 22),
    ("大雪", "水", 12, 7), ("冬至", "水", 12, 21),
]

# 五行 → 脏腑 映射
WUXING_ZANGFU = {
    "木": {"脏": "肝", "腑": "胆", "部位": "目/筋/爪甲", "季节": "春"},
    "火": {"脏": "心", "腑": "小肠", "部位": "舌/血脉/面部", "季节": "夏"},
    "土": {"脏": "脾", "腑": "胃", "部位": "口/唇/肌肉", "季节": "四季末"},
    "金": {"脏": "肺", "腑": "大肠", "部位": "鼻/皮肤/毛发", "季节": "秋"},
    "水": {"脏": "肾", "腑": "膀胱", "部位": "耳/骨骼/头发", "季节": "冬"},
}

# 地支六冲
SIX_CHONG = {("子", "午"), ("午", "子"), ("丑", "未"), ("未", "丑"),
             ("寅", "申"), ("申", "寅"), ("卯", "酉"), ("酉", "卯"),
             ("辰", "戌"), ("戌", "辰"), ("巳", "亥"), ("亥", "巳")}

# 地支六合
SIX_HE = {("子", "丑"), ("丑", "子"), ("寅", "亥"), ("亥", "寅"),
          ("卯", "戌"), ("戌", "卯"), ("辰", "酉"), ("酉", "辰"),
          ("巳", "申"), ("申", "巳"), ("午", "未"), ("未", "午")}


# === sxtwl 排盘核心（可选依赖） ===

def _get_sxtwl():
    """懒加载 sxtwl"""
    try:
        import sxtwl
        return sxtwl
    except ImportError:
        return None


def get_day_gz(target_date):
    """获取指定日期的日干支"""
    sxtwl = _get_sxtwl()
    if sxtwl is None:
        raise RuntimeError("sxtwl 未安装，请 pip install sxtwl")
    day = sxtwl.fromSolar(target_date.year, target_date.month, target_date.day)
    gz = day.getDayGZ()
    return TG[gz.tg], DZ[gz.dz]


def get_month_gz(target_date):
    """获取指定日期的月干支（节气后）"""
    sxtwl = _get_sxtwl()
    if sxtwl is None:
        raise RuntimeError("sxtwl 未安装")
    day = sxtwl.fromSolar(target_date.year, target_date.month, target_date.day)
    gz = day.getMonthGZ()
    return TG[gz.tg], DZ[gz.dz]


def get_year_gz(target_date):
    """获取指定日期的年干支（立春后）"""
    sxtwl = _get_sxtwl()
    if sxtwl is None:
        raise RuntimeError("sxtwl 未安装")
    day = sxtwl.fromSolar(target_date.year, target_date.month, target_date.day)
    gz = day.getYearGZ()
    return TG[gz.tg], DZ[gz.dz]


# === 十神 / 强弱 / 喜忌神 ===

def get_ten_god(tg, daymaster):
    """获取十神名称"""
    dm_wx = TG_WUXING[daymaster]
    tg_wx = TG_WUXING[tg]
    dm_yy = TG_YINYANG[daymaster]
    tg_yy = TG_YINYANG[tg]

    if tg == daymaster:
        return "比肩" if dm_yy == tg_yy else "劫财"

    # 生我者 = 印（tg 生 dm）
    if SHENG.get(tg_wx) == dm_wx:
        return "偏印" if dm_yy != tg_yy else "正印"
    # 我生者 = 食伤（dm 生 tg）
    if SHENG.get(dm_wx) == tg_wx:
        return "食神" if dm_yy == tg_yy else "伤官"
    # 克我者 = 官杀（tg 克 dm）
    if KE.get(tg_wx) == dm_wx:
        return "七杀" if dm_yy == tg_yy else "正官"
    # 我克者 = 财（dm 克 tg）
    if KE.get(dm_wx) == tg_wx:
        return "偏财" if dm_yy == tg_yy else "正财"

    return "未知"


def get_daymaster_strength(bazi_chart):
    """
    判断日主强弱
    简化算法: 统计四柱天干地支藏干的五行力量
    Returns: '旺' | '中和' | '弱'
    """
    daymaster = bazi_chart.get("日柱", (None, None))[0]
    if not daymaster:
        return "中和"
    dm_wx = TG_WUXING[daymaster]

    # 五行力量分
    scores = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}
    weights = {"年柱": 0.8, "月柱": 1.5, "日柱": 1.0, "时柱": 0.8}  # 月令权重最大

    for pillar_name, pillar in bazi_chart.items():
        if not pillar or pillar == (None, None):
            continue
        tg, dz = pillar
        w = weights.get(pillar_name, 1.0)
        # 天干
        scores[TG_WUXING[tg]] += 1.0 * w
        # 地支藏干
        cangans = DZ_CANGAN.get(dz, [])
        weights_cg = [0.6, 0.3, 0.1]
        for i, cg in enumerate(cangans):
            if i < len(weights_cg):
                scores[TG_WUXING[cg]] += weights_cg[i] * w

    # 日主力量 = 自己 + 生我者（印）
    sheng_map = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
    sheng_wx = sheng_map[dm_wx]

    dm_total = scores[dm_wx] + scores[sheng_wx] * 0.6
    # 失令判定: 月支不是日主五行
    month_dz = bazi_chart.get("月柱", (None, None))[1]
    if month_dz and DZ_WUXING[month_dz] != dm_wx:
        dm_total *= 0.8  # 失令减分

    if dm_total >= 4.0:
        return "旺"
    elif dm_total >= 2.5:
        return "中和"
    else:
        return "弱"


def get_xishen_jishen(bazi_chart):
    """
    根据日主强弱返回喜忌神五行集合
    Returns: (xishen_set, jishen_set) - 都是 {'木','火',...} 五行集合

    身旺: 喜 食伤(我生) + 财(我克) + 官杀(克我)  →  泄耗克
          忌 印(生我) + 比劫(同我)  →  生扶
    身弱: 喜 印 + 比劫  →  生扶
          忌 食伤 + 财 + 官杀  →  泄耗克
    """
    strength = get_daymaster_strength(bazi_chart)
    daymaster = bazi_chart.get("日柱", (None, None))[0]
    if not daymaster:
        return set(), set()

    dm_wx = TG_WUXING[daymaster]
    sheng_map = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
    wo_sheng = SHENG[dm_wx]  # 我生 = 食伤
    wo_ke_map = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
    ke_wo_map = {"木": "金", "火": "水", "土": "木", "金": "火", "水": "土"}

    if strength == "旺":
        xishen = {wo_sheng, wo_ke_map[dm_wx], ke_wo_map[dm_wx]}
        jishen = {sheng_map[dm_wx], dm_wx}
    elif strength == "弱":
        xishen = {sheng_map[dm_wx], dm_wx}
        jishen = {wo_sheng, wo_ke_map[dm_wx], ke_wo_map[dm_wx]}
    else:  # 中和
        # 中和则不强求喜忌，看具体组合
        xishen = set()
        jishen = set()

    return xishen, jishen


# === 核心打分函数 ===

def score_gz_to_chart(gz, bazi_chart):
    """
    给定一个干支 (tg, dz)，计算它对命主的喜忌贡献分数
    Returns: -3..+3 整数（夹紧）
    """
    daymaster = bazi_chart.get("日柱", (None, None))[0]
    if not daymaster:
        return 0

    tg, dz = gz
    xishen, jishen = get_xishen_jishen(bazi_chart)

    score = 0.0

    # 1. 天干喜忌 (权重 1.0)
    tg_wx = TG_WUXING[tg]
    if xishen and tg_wx in xishen:
        score += 1.0
    elif jishen and tg_wx in jishen:
        score -= 1.0

    # 2. 地支本气喜忌 (权重 1.0)
    cangans = DZ_CANGAN.get(dz, [])
    if cangans:
        benqi_wx = TG_WUXING[cangans[0]]
        if xishen and benqi_wx in xishen:
            score += 1.0
        elif jishen and benqi_wx in jishen:
            score -= 1.0

    # 3. 地支中余气喜忌 (权重 0.3 + 0.1)
    if len(cangans) > 1 and xishen and jishen:
        zhongqi_wx = TG_WUXING[cangans[1]]
        if zhongqi_wx in xishen:
            score += 0.3
        elif zhongqi_wx in jishen:
            score -= 0.3
    if len(cangans) > 2 and xishen and jishen:
        yuqi_wx = TG_WUXING[cangans[2]]
        if yuqi_wx in xishen:
            score += 0.1
        elif yuqi_wx in jishen:
            score -= 0.1

    # 4. 地支与日支关系
    day_dz = bazi_chart["日柱"][1]
    if day_dz:
        if (day_dz, dz) in SIX_CHONG:
            score -= 1.0  # 六冲最凶
        elif (day_dz, dz) in SIX_HE:
            score += 0.5  # 六合次吉

    return max(-3, min(3, round(score)))


def score_to_stars(score):
    """-3..+3 → 1-5 星（保留半星）"""
    score = max(-3, min(3, score))
    stars = 3.0 + score * 2.0 / 3.0  # 线性
    return round(stars * 2) / 2


def stars_display(stars):
    """1-5 星 → ★/☆ 字符串"""
    full = int(stars)
    half = 1 if (stars * 2) % 2 == 1 else 0
    return "★" * full + "☆" * (5 - full - half) + ("½" if half else "")


# === 时间辅助 ===

def get_current_jieqi(target_date):
    """获取当前节气（简化版，按月份日期阈值近似）"""
    m, d = target_date.month, target_date.day
    # 从年末到年初倒序遍历
    for jieqi_name, wuxing, jm, jd in reversed(JIEQI_TABLE):
        if (m, d) >= (jm, jd):
            return jieqi_name, wuxing
    # 跨年（1月初还在上一年节气）
    return JIEQI_TABLE[-1][0], JIEQI_TABLE[-1][1]


def get_current_season(target_date):
    """获取当前季节"""
    m = target_date.month
    if m in (3, 4, 5):
        return "春"
    elif m in (6, 7, 8):
        return "夏"
    elif m in (9, 10, 11):
        return "秋"
    else:
        return "冬"


# === 运势 4 维度 ===

def calc_daily_fortune(bazi_chart, target_date):
    """今日运势：基于今日日柱对日主的喜忌"""
    today_gz = get_day_gz(target_date)
    score = score_gz_to_chart(today_gz, bazi_chart)
    stars = score_to_stars(score)

    daymaster = bazi_chart["日柱"][0]
    ten_god = get_ten_god(today_gz[0], daymaster)
    dz_wx = DZ_WUXING[today_gz[1]]

    # 分维度（基于十神微调）
    ten_god_bonus = {
        "正官": {"事业": 0.5}, "七杀": {"事业": 0.5, "人际": -0.5},
        "食神": {"财运": 0.5, "人际": 0.5}, "伤官": {"事业": 0.5, "人际": -0.5},
        "正财": {"财运": 0.5, "感情": 0.5}, "偏财": {"财运": 0.5},
        "比肩": {"人际": 0.5}, "劫财": {"财运": -0.5, "人际": 0.5},
        "正印": {"事业": 0.5}, "偏印": {"事业": 0.5},
    }
    bonus = ten_god_bonus.get(ten_god, {})

    dims = {
        "整体": stars,
        "事业": max(1, min(5, round((stars + bonus.get("事业", 0)) * 2) / 2)),
        "财运": max(1, min(5, round((stars + bonus.get("财运", 0)) * 2) / 2)),
        "感情": max(1, min(5, round((stars + bonus.get("感情", 0)) * 2) / 2)),
        "人际": max(1, min(5, round((stars + bonus.get("人际", 0)) * 2) / 2)),
    }

    return {
        "日期": target_date.isoformat(),
        "干支": f"{today_gz[0]}{today_gz[1]}",
        "十神": ten_god,
        "五行": dz_wx,
        "分数": score,
        "维度": dims,
    }


def calc_weekly_fortune(bazi_chart, target_date):
    """本周运势：7 天日柱综合"""
    monday = target_date - timedelta(days=target_date.weekday())

    daily = []
    for i in range(7):
        d = monday + timedelta(days=i)
        gz = get_day_gz(d)
        score = score_gz_to_chart(gz, bazi_chart)
        daily.append({"日期": d.isoformat(), "干支": f"{gz[0]}{gz[1]}", "分": score, "星": score_to_stars(score)})

    avg_score = sum(x["分"] for x in daily) / 7
    avg_stars = score_to_stars(avg_score)

    best = max(daily, key=lambda x: x["分"])
    worst = min(daily, key=lambda x: x["分"])

    return {
        "周开始": monday.isoformat(),
        "周结束": (monday + timedelta(days=6)).isoformat(),
        "平均分": round(avg_score, 2),
        "星数": avg_stars,
        "日明细": daily,
        "最吉日": {"日期": best["日期"], "干支": best["干支"], "分": best["分"]},
        "最凶日": {"日期": worst["日期"], "干支": worst["干支"], "分": worst["分"]},
    }


def calc_monthly_fortune(bazi_chart, target_date):
    """本月运势：月柱 + 流年"""
    month_gz = get_month_gz(target_date)
    year_gz = get_year_gz(target_date)

    month_score = score_gz_to_chart(month_gz, bazi_chart)
    year_score = score_gz_to_chart(year_gz, bazi_chart)
    combined = round((month_score * 0.6 + year_score * 0.4), 2)

    return {
        "月份": f"{target_date.year}-{target_date.month:02d}",
        "月柱": f"{month_gz[0]}{month_gz[1]}",
        "流年": f"{year_gz[0]}{year_gz[1]}",
        "月柱分": month_score,
        "流年分": year_score,
        "综合分": combined,
        "星数": score_to_stars(combined),
    }


def calc_yearly_fortune(bazi_chart, target_date):
    """本年运势：流年 vs 大运（简化）"""
    year_gz = get_year_gz(target_date)
    year_score = score_gz_to_chart(year_gz, bazi_chart)

    return {
        "年份": target_date.year,
        "流年": f"{year_gz[0]}{year_gz[1]}",
        "分数": year_score,
        "星数": score_to_stars(year_score),
    }


# === 健康 4 维度 ===

def _health_status(wuxing, bazi_chart):
    """五行 vs 喜忌 → 状态描述"""
    xishen, jishen = get_xishen_jishen(bazi_chart)
    if xishen and wuxing in xishen:
        return "得助"
    if jishen and wuxing in jishen:
        return "受制"
    return "平和"


def _health_advice(wuxing, zangfu, status):
    """根据五行/脏腑/状态生成健康建议"""
    if status == "得助":
        return f"{zangfu['脏']}气充足，{zangfu['部位']}状态良好，适度活动即可，避免过补"
    if status == "受制":
        return f"{zangfu['脏']}气偏亢，{zangfu['部位']}需减压，建议清淡饮食、规律作息"
    return f"{zangfu['脏']}气平稳，{zangfu['部位']}无需特别调理，顺其自然"


def calc_daily_health(bazi_chart, target_date):
    """今日健康：今日日支五行对应脏腑"""
    today_gz = get_day_gz(target_date)
    today_wx = DZ_WUXING[today_gz[1]]
    zangfu = WUXING_ZANGFU[today_wx]
    status = _health_status(today_wx, bazi_chart)

    return {
        "日期": target_date.isoformat(),
        "干支": f"{today_gz[0]}{today_gz[1]}",
        "五行": today_wx,
        "状态": status,
        "脏腑": f"{zangfu['脏']}/{zangfu['腑']}",
        "部位": zangfu["部位"],
        "建议": _health_advice(today_wx, zangfu, status),
    }


def calc_solar_term_health(bazi_chart, target_date):
    """节气健康：当前节气五行对应脏腑"""
    jieqi, jieqi_wx = get_current_jieqi(target_date)
    zangfu = WUXING_ZANGFU[jieqi_wx]
    status = _health_status(jieqi_wx, bazi_chart)

    return {
        "节气": jieqi,
        "五行": jieqi_wx,
        "状态": status,
        "脏腑": f"{zangfu['脏']}/{zangfu['腑']}",
        "部位": zangfu["部位"],
        "建议": f"{jieqi}时节{zangfu['脏']}气{status}，{_health_advice(jieqi_wx, zangfu, status)}",
    }


def calc_seasonal_health(bazi_chart, target_date):
    """季节健康：季节当令五行"""
    season = get_current_season(target_date)
    season_wx_map = {"春": "木", "夏": "火", "秋": "金", "冬": "水"}
    season_wx = season_wx_map[season]
    zangfu = WUXING_ZANGFU[season_wx]

    return {
        "季节": season,
        "五行": season_wx,
        "脏腑": f"{zangfu['脏']}/{zangfu['腑']}",
        "部位": zangfu["部位"],
        "建议": f"{season}季{season_wx}气当令，{zangfu['脏']}{zangfu['腑']}功能活跃，重点保养{zangfu['部位']}",
    }


def calc_yearly_health(bazi_chart, target_date):
    """年度健康：流年五行对应脏腑"""
    year_gz = get_year_gz(target_date)
    year_wx = TG_WUXING[year_gz[0]]
    zangfu = WUXING_ZANGFU[year_wx]
    status = _health_status(year_wx, bazi_chart)

    if status == "得助":
        advice = f"{target_date.year}年{zangfu['脏']}气充足，{zangfu['部位']}保养为主，忌过补"
    elif status == "受制":
        advice = f"{target_date.year}年{zangfu['脏']}气偏亢，全年重点关注{zangfu['部位']}调养"
    else:
        advice = f"{target_date.year}年{zangfu['脏']}气平稳，{zangfu['部位']}顺其自然"

    return {
        "年份": target_date.year,
        "流年": f"{year_gz[0]}{year_gz[1]}",
        "五行": year_wx,
        "状态": status,
        "脏腑": f"{zangfu['脏']}/{zangfu['腑']}",
        "建议": advice,
    }


# === 主入口 ===

def generate_full_report(bazi_chart, target_date=None):
    """生成完整 8 维度报告 (dict)"""
    if target_date is None:
        target_date = date.today()

    return {
        "查询日期": target_date.isoformat(),
        "日主": bazi_chart.get("日柱", (None, None))[0],
        "日主强弱": get_daymaster_strength(bazi_chart),
        "喜神": list(get_xishen_jishen(bazi_chart)[0]),
        "忌神": list(get_xishen_jishen(bazi_chart)[1]),
        "运势": {
            "今日": calc_daily_fortune(bazi_chart, target_date),
            "本周": calc_weekly_fortune(bazi_chart, target_date),
            "本月": calc_monthly_fortune(bazi_chart, target_date),
            "本年": calc_yearly_fortune(bazi_chart, target_date),
        },
        "健康": {
            "今日": calc_daily_health(bazi_chart, target_date),
            "节气": calc_solar_term_health(bazi_chart, target_date),
            "季节": calc_seasonal_health(bazi_chart, target_date),
            "本年": calc_yearly_health(bazi_chart, target_date),
        },
    }


def format_markdown(report):
    """生成可展示的 markdown 文本"""
    r = report
    fy = r["运势"]
    jk = r["健康"]
    lines = []

    lines.append(f"## 🔮 运势 + 🏥 健康 综合分析（{r['查询日期']}）")
    lines.append("")
    lines.append(f"**日主**：{r['日主']}（{r['日主强弱']}）")
    lines.append(f"**喜神**：{', '.join(r['喜神']) if r['喜神'] else '（中和）'}")
    lines.append(f"**忌神**：{', '.join(r['忌神']) if r['忌神'] else '（中和）'}")
    lines.append("")

    # === 运势 4 维度 ===
    lines.append("### 🔮 运势")
    lines.append("")

    # 今日
    d = fy["今日"]
    lines.append(f"**📅 今日运势**（{d['日期']} {d['干支']}日 / {d['十神']}）")
    lines.append(f"整体: {stars_display(d['维度']['整体'])}  事业: {stars_display(d['维度']['事业'])}  财运: {stars_display(d['维度']['财运'])}  感情: {stars_display(d['维度']['感情'])}  人际: {stars_display(d['维度']['人际'])}")
    lines.append("")

    # 本周
    w = fy["本周"]
    lines.append(f"**📆 本周运势**（{w['周开始']} ~ {w['周结束']}）")
    lines.append(f"整体: {stars_display(w['星数'])}（平均分 {w['平均分']}）")
    lines.append(f"最吉: {w['最吉日']['日期']} {w['最吉日']['干支']}（{w['最吉日']['分']:+d}）  最凶: {w['最凶日']['日期']} {w['最凶日']['干支']}（{w['最凶日']['分']:+d}）")
    lines.append("")

    # 本月
    m = fy["本月"]
    lines.append(f"**🗓️ 本月运势**（{m['月份']}）")
    lines.append(f"月柱 {m['月柱']} + 流年 {m['流年']} → {stars_display(m['星数'])}（{m['综合分']:+}）")
    lines.append("")

    # 本年
    y = fy["本年"]
    lines.append(f"**🎊 本年运势**（{y['年份']} {y['流年']}年）")
    lines.append(f"流年: {stars_display(y['星数'])}（{y['分数']:+d}）")
    lines.append("")

    # === 健康 4 维度 ===
    lines.append("### 🏥 健康")
    lines.append("")

    # 今日
    d = jk["今日"]
    lines.append(f"**📅 今日健康**（{d['干支']}日 / {d['五行']}气{d['状态']}）")
    lines.append(f"重点脏腑: {d['脏腑']}  部位: {d['部位']}")
    lines.append(f"建议: {d['建议']}")
    lines.append("")

    # 节气
    j = jk["节气"]
    lines.append(f"**☯️ 节气健康**（当前: {j['节气']} / {j['五行']}气{j['状态']}）")
    lines.append(f"重点脏腑: {j['脏腑']}  部位: {j['部位']}")
    lines.append(f"建议: {j['建议']}")
    lines.append("")

    # 季节
    s = jk["季节"]
    lines.append(f"**🌸 季节健康**（{s['季节']}季 / {s['五行']}气当令）")
    lines.append(f"重点脏腑: {s['脏腑']}  部位: {s['部位']}")
    lines.append(f"建议: {s['建议']}")
    lines.append("")

    # 本年
    y = jk["本年"]
    lines.append(f"**🎊 年度健康**（{y['年份']} {y['流年']}年 / {y['五行']}气{y['状态']}）")
    lines.append(f"建议: {y['建议']}")
    lines.append("")

    lines.append("---")
    lines.append("*命理分析仅供文化参考，**健康问题请遵医嘱**。*")
    return "\n".join(lines)


# === CLI ===

if __name__ == "__main__":
    import json
    import sys

    # 默认测试用例
    sample_chart = {
        "年柱": ("庚", "午"),
        "月柱": ("辛", "巳"),
        "日柱": ("甲", "子"),
        "时柱": ("己", "巳"),
    }

    target = date.today()
    if len(sys.argv) > 1:
        # python fortune_health.py 2026-06-29
        from datetime import datetime
        target = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()

    report = generate_full_report(sample_chart, target)
    print(format_markdown(report))
