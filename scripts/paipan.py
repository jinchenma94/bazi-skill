#!/usr/bin/env python3
"""
八字排盘脚本 —— 使用 lunar-python 库做精确计算。

用法：
    python3 paipan.py --solar 1993-12-20 --time 10:30 --gender male
    python3 paipan.py --lunar 1993-11-07 --time 子 --gender female

输出 JSON，包含四柱、藏干、十神、起运、顺逆两套大运表。

依赖：pip install lunar-python
"""

import argparse
import json
import sys
from lunar_python import Solar, Lunar


SHICHEN_MAP = {
    '子': 0, '丑': 2, '寅': 4, '卯': 6, '辰': 8, '巳': 10,
    '午': 12, '未': 14, '申': 16, '酉': 18, '戌': 20, '亥': 22,
}

GAN_YIN_YANG = {
    '甲': '阳', '丙': '阳', '戊': '阳', '庚': '阳', '壬': '阳',
    '乙': '阴', '丁': '阴', '己': '阴', '辛': '阴', '癸': '阴',
}

# 十神映射：以日干为基准，对其他干的关系
WUXING = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
    '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
}

SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


def get_shishen(day_gan: str, other_gan: str) -> str:
    """以日干为我，判断 other_gan 是何十神。"""
    if other_gan == day_gan:
        return '日主'
    me_wx = WUXING[day_gan]
    other_wx = WUXING[other_gan]
    me_yy = GAN_YIN_YANG[day_gan]
    other_yy = GAN_YIN_YANG[other_gan]
    same_yy = (me_yy == other_yy)

    if me_wx == other_wx:
        return '比肩' if same_yy else '劫财'
    if SHENG[other_wx] == me_wx:  # other 生 me
        return '偏印' if same_yy else '正印'
    if SHENG[me_wx] == other_wx:  # me 生 other
        return '食神' if same_yy else '伤官'
    if KE[other_wx] == me_wx:  # other 克 me
        return '七杀' if same_yy else '正官'
    if KE[me_wx] == other_wx:  # me 克 other
        return '偏财' if same_yy else '正财'
    return '?'


def parse_time(time_str: str) -> tuple[int, int]:
    """解析时间。支持 'HH:MM' 或 时辰汉字。
    时辰对应区间：子23:00-01:00, 丑01:00-03:00, ..., 亥21:00-23:00
    传时辰汉字时，取该时辰区间内的稳定中点（避开早晚子时争议）。
    子时默认取 00:30（早子时），如需夜子时请用 HH:MM 显式传 23:30。
    """
    if ':' in time_str:
        h, m = time_str.split(':')
        return int(h), int(m)
    # 时辰中点（起始小时 + 1小时 = 中点；子时特殊处理为 00:30）
    shichen_midpoint = {
        '子': (0, 30), '丑': (2, 0), '寅': (4, 0), '卯': (6, 0),
        '辰': (8, 0), '巳': (10, 0), '午': (12, 0), '未': (14, 0),
        '申': (16, 0), '酉': (18, 0), '戌': (20, 0), '亥': (22, 0),
    }
    if time_str in shichen_midpoint:
        return shichen_midpoint[time_str]
    raise ValueError(f"无法解析时间: {time_str}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solar', help='阳历日期 YYYY-MM-DD')
    ap.add_argument('--lunar', help='农历日期 YYYY-MM-DD（月日为农历）')
    ap.add_argument('--leap', action='store_true', help='农历为闰月')
    ap.add_argument('--time', required=True, help="时间 'HH:MM' 或时辰汉字 (子/丑/...)")
    ap.add_argument('--gender', required=True, choices=['male', 'female', '男', '女'])
    args = ap.parse_args()

    if not args.solar and not args.lunar:
        print("必须提供 --solar 或 --lunar", file=sys.stderr)
        sys.exit(1)

    hour, minute = parse_time(args.time)

    if args.solar:
        y, m, d = map(int, args.solar.split('-'))
        solar = Solar.fromYmdHms(y, m, d, hour, minute, 0)
    else:
        y, m, d = map(int, args.lunar.split('-'))
        if args.leap:
            m = -m  # lunar-python 用负数表示闰月
        lunar = Lunar.fromYmdHms(y, m, d, hour, minute, 0)
        solar = lunar.getSolar()

    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    is_male = args.gender in ('male', '男')
    gender_code = 1 if is_male else 0

    # 四柱
    year_gz = ec.getYear()
    month_gz = ec.getMonth()
    day_gz = ec.getDay()
    time_gz = ec.getTime()

    day_gan = ec.getDayGan()

    pillars = {}
    藏干_map = {
        '子': ['癸'], '丑': ['己', '癸', '辛'], '寅': ['甲', '丙', '戊'],
        '卯': ['乙'], '辰': ['戊', '乙', '癸'], '巳': ['丙', '庚', '戊'],
        '午': ['丁', '己'], '未': ['己', '丁', '乙'], '申': ['庚', '壬', '戊'],
        '酉': ['辛'], '戌': ['戊', '辛', '丁'], '亥': ['壬', '甲'],
    }

    for label, gz in [('year', year_gz), ('month', month_gz), ('day', day_gz), ('time', time_gz)]:
        gan = gz[0]
        zhi = gz[1]
        canggan = 藏干_map[zhi]
        pillars[label] = {
            'ganzhi': gz,
            'gan': gan,
            'zhi': zhi,
            'gan_shishen': get_shishen(day_gan, gan) if label != 'day' else '日主',
            'canggan': canggan,
            'canggan_shishen': [get_shishen(day_gan, g) for g in canggan],
        }

    # ============ 起运 + 大运 ============
    # 固定规则：男统一顺排、女统一逆排（现代主流软件惯例）
    # lunar-python 库内部规则恰好是 阳男阴女顺、阴男阳女逆（经典派）；
    # 要拿"男顺女逆"，需要根据年干阴阳决定是否传反向性别给库：
    #   - 男 + 阳年 → 库本就顺排 → gender_code=1（男）
    #   - 男 + 阴年 → 库本会逆排 → 传 0（女）骗它给顺排
    #   - 女 + 阳年 → 库本会逆排 → 直接 gender_code=0（女）
    #   - 女 + 阴年 → 库本会顺排 → 传 1（男）骗它给逆排
    year_gan = year_gz[0]
    is_yang_year = GAN_YIN_YANG[year_gan] == '阳'
    # 我们想要的方向：男=顺、女=逆
    want_forward = is_male
    # 库默认规则：阳男阴女顺
    lib_forward_with_real_gender = (is_yang_year == is_male)  # 即 阳男 或 阴女
    if want_forward == lib_forward_with_real_gender:
        effective_gender = gender_code
    else:
        effective_gender = 1 - gender_code

    yun = ec.getYun(effective_gender)
    dayun_steps = []
    for d in yun.getDaYun()[:9]:
        dayun_steps.append({
            'start_age': d.getStartAge(),
            'end_age': d.getEndAge(),
            'ganzhi': d.getGanZhi(),
            'start_year': d.getStartYear(),
        })

    dayun = {
        'direction': '顺排' if want_forward else '逆排',
        'rule': '男统一顺排、女统一逆排（现代软件惯例）',
        'start_years': yun.getStartYear(),
        'start_months': yun.getStartMonth(),
        'start_days': yun.getStartDay(),
        'start_age_rounded': round(yun.getStartYear() + yun.getStartMonth()/12 + yun.getStartDay()/365),
        'jiao_yun_solar': yun.getStartSolar().toYmd(),
        'steps': dayun_steps,
    }

    result = {
        'input': {
            'solar': solar.toYmd() + ' ' + f'{hour:02d}:{minute:02d}',
            'lunar': lunar.toString(),
            'gender': '男' if is_male else '女',
        },
        'pillars': pillars,
        'day_master': day_gan,
        'day_master_wuxing': WUXING[day_gan],
        'year_gan_yinyang': GAN_YIN_YANG[year_gan],
        'dayun': dayun,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
