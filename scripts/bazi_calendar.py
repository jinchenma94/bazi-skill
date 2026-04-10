#!/usr/bin/env python3
"""Deterministic helpers for Bazi pillars and Da Yun setup.

Exact pillar calculation depends on solar terms. This script uses the optional
`sxtwl` package for pillar conversion when available. Da Yun direction and
start-age calculation can also be computed from supplied month pillar and the
relevant previous/next solar term timestamp.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
YANG_STEMS = {"甲", "丙", "戊", "庚", "壬"}
YIN_STEMS = {"乙", "丁", "己", "辛", "癸"}
SEX_ALIASES = {
    "male": "male",
    "m": "male",
    "男": "male",
    "female": "female",
    "f": "female",
    "女": "female",
}


@dataclass(frozen=True)
class DayunResult:
    direction: str
    start_age_years: float | None
    start_age_text: str | None
    dayun: list[str]
    note: str


def ganzhi_from_indexes(tg: int, dz: int) -> str:
    return GAN[tg % 10] + ZHI[dz % 12]


def ganzhi_index(pillar: str) -> int:
    if len(pillar) != 2 or pillar[0] not in GAN or pillar[1] not in ZHI:
        raise ValueError(f"Invalid pillar: {pillar}")
    stem_i = GAN.index(pillar[0])
    branch_i = ZHI.index(pillar[1])
    for i in range(60):
        if i % 10 == stem_i and i % 12 == branch_i:
            return i
    raise ValueError(f"Stem/branch parity mismatch: {pillar}")


def normalize_sex(value: str) -> str:
    normalized = SEX_ALIASES.get(value.strip().lower(), SEX_ALIASES.get(value.strip()))
    if normalized is None:
        raise ValueError("sex must be male/female/男/女")
    return normalized


def dayun_direction(year_stem: str, sex: str) -> str:
    if year_stem not in GAN:
        raise ValueError("year_stem must be one Chinese heavenly stem")
    sex_norm = normalize_sex(sex)
    is_yang = year_stem in YANG_STEMS
    if (sex_norm == "male" and is_yang) or (sex_norm == "female" and not is_yang):
        return "forward"
    return "reverse"


def start_age_from_term(birth: datetime, term: datetime) -> tuple[float, str]:
    delta_days = abs((term - birth).total_seconds()) / 86400
    years = delta_days / 3.0
    whole_years = int(years)
    months_float = (years - whole_years) * 12
    whole_months = int(months_float)
    days = round((months_float - whole_months) * 30)
    text = f"{whole_years}年{whole_months}个月{days}天"
    return round(years, 3), text


def build_dayun(month_pillar: str, direction: str, count: int) -> list[str]:
    start = ganzhi_index(month_pillar)
    step = 1 if direction == "forward" else -1
    return [ganzhi_from_indexes((start + step * i) % 60, (start + step * i) % 60) for i in range(1, count + 1)]


def command_dayun(args: argparse.Namespace) -> dict[str, Any]:
    direction = dayun_direction(args.year_stem, args.sex)
    start_age_years = args.start_age_years
    start_age_text = None
    note = "Da Yun direction follows 阳年男/阴年女顺排，阴年男/阳年女逆排。"

    if args.birth and args.nearest_term:
        birth = datetime.fromisoformat(args.birth)
        term = datetime.fromisoformat(args.nearest_term)
        start_age_years, start_age_text = start_age_from_term(birth, term)
        note += " 起运按三天一岁折算；nearest_term must be the relevant next/previous solar term for the chosen direction."
    elif start_age_years is not None:
        note += " 起运年龄由用户提供。"
    else:
        note += " 未提供 nearest_term 或 start_age_years，只输出顺逆和大运序列。"

    result = DayunResult(
        direction=direction,
        start_age_years=start_age_years,
        start_age_text=start_age_text,
        dayun=build_dayun(args.month_pillar, direction, args.count),
        note=note,
    )
    return asdict(result)


def command_pillars(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import sxtwl  # type: ignore
    except ImportError:
        return {
            "ok": False,
            "error": "Exact pillar calculation requires optional dependency `sxtwl`. Install with `pip install -r scripts/requirements.txt`.",
        }

    date = datetime.fromisoformat(f"{args.date}T{args.time or '12:00'}")
    try:
        day = sxtwl.fromSolar(date.year, date.month, date.day)
        hour = date.hour
        year_gz = day.getYearGZ()
        month_gz = day.getMonthGZ()
        day_gz = day.getDayGZ()
        hour_gz = day.getHourGZ(hour)
        return {
            "ok": True,
            "date": args.date,
            "time": args.time,
            "location": args.location,
            "pillars": {
                "year": ganzhi_from_indexes(year_gz.tg, year_gz.dz),
                "month": ganzhi_from_indexes(month_gz.tg, month_gz.dz),
                "day": ganzhi_from_indexes(day_gz.tg, day_gz.dz),
                "hour": ganzhi_from_indexes(hour_gz.tg, hour_gz.dz),
            },
            "note": "Year/month pillars use sxtwl solar-term logic. Check true solar time and late-zi-hour convention manually when relevant.",
        }
    except Exception as exc:  # pragma: no cover - depends on optional package API.
        return {
            "ok": False,
            "error": f"sxtwl pillar calculation failed: {exc}",
        }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    pillars = subparsers.add_parser("pillars", help="Calculate four pillars via optional sxtwl.")
    pillars.add_argument("--date", required=True, help="Gregorian date, YYYY-MM-DD.")
    pillars.add_argument("--time", default="12:00", help="Local clock time, HH:MM.")
    pillars.add_argument("--location", default="", help="Birth location label for output notes.")

    dayun = subparsers.add_parser("dayun", help="Calculate Da Yun direction and sequence.")
    dayun.add_argument("--sex", required=True, help="male/female/男/女.")
    dayun.add_argument("--year-stem", required=True, help="Birth year heavenly stem, e.g. 丙.")
    dayun.add_argument("--month-pillar", required=True, help="Birth month pillar, e.g. 辛卯.")
    dayun.add_argument("--birth", help="Birth local datetime, ISO format, e.g. 1996-03-08T09:05:00.")
    dayun.add_argument("--nearest-term", help="Relevant solar term datetime, ISO format.")
    dayun.add_argument("--start-age-years", type=float, help="Known start age in decimal years.")
    dayun.add_argument("--count", type=int, default=10, help="Number of Da Yun pillars to output.")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.command == "pillars":
            payload = command_pillars(args)
            exit_code = 0 if payload.get("ok") else 2
        elif args.command == "dayun":
            payload = command_dayun(args)
            exit_code = 0
        else:
            raise AssertionError(args.command)
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        exit_code = 1

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
