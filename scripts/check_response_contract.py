#!/usr/bin/env python3
"""Check whether a Bazi response satisfies the skill's output contract.

This is a lightweight regression helper. It checks for required structural
signals and banned phrases; it does not judge whether the Bazi reasoning is
correct.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BANNED_PHRASES = (
    "某大师说",
    "命中注定",
    "一定会破产",
    "必死",
    "绝症",
    "袁天罡断你命中注定",
    "李淳风预言",
    "只因五行缺",
    "所以必须补",
)


COMMON_REQUIRED = {
    "general": (
        ("direct_judgement", ("铁口", "判断", "结论", "断语")),
        ("evidence", ("依据", "命局", "月令", "日主", "十神", "格局")),
        ("method", ("名家方法", "按", "徐子平", "沈孝瞻", "张楠", "任铁樵", "韦千里", "袁树珊", "徐乐吾")),
        ("real_world", ("现实", "落点", "表现", "职业", "关系", "资产", "现金流")),
        ("calibration", ("置信度", "校准", "待确认", "反馈")),
    ),
    "wealth": (
        ("income_model", ("收入能力", "收入结构", "经营模式")),
        ("liquidity", ("现金流", "流动性", "周转")),
        ("asset_actions", ("资产动作", "项目投入", "负债", "配置")),
        ("felt_security", ("财富安全感", "安全感", "体感")),
        ("wealth_methods", ("李虚中", "徐子平", "张楠", "韦千里")),
    ),
    "classical": (
        ("classical_boundary", ("四柱", "命局", "依据", "证据")),
        ("role_boundary", ("李淳风", "袁天罡", "古法", "口吻", "象法")),
        ("legend_boundary", ("传说", "预言", "不作", "不当作", "边界")),
    ),
    "dayun": (
        ("dayun", ("大运", "流年")),
        ("trigger", ("触发", "冲", "合", "刑", "害", "伏吟", "反吟")),
        ("confidence", ("置信度", "A", "B", "C")),
    ),
    "health": (
        ("constitution", ("体质", "寒暖", "燥湿", "五行")),
        ("medical_boundary", ("医学", "检查", "诊断", "医生")),
    ),
}


def contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def check_required(text: str, mode: str) -> list[str]:
    missing: list[str] = []
    required = list(COMMON_REQUIRED["general"])
    if mode != "general":
        required.extend(COMMON_REQUIRED[mode])

    for key, words in required:
        if not contains_any(text, words):
            missing.append(f"{key}: expected one of {', '.join(words)}")
    return missing


def check_banned(text: str) -> list[str]:
    return [phrase for phrase in BANNED_PHRASES if phrase in text]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Response text/markdown file to check.")
    parser.add_argument(
        "--mode",
        choices=sorted(COMMON_REQUIRED.keys()),
        default="general",
        help="Contract mode to check.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    text = Path(args.path).read_text(encoding="utf-8")
    missing = check_required(text, args.mode)
    banned = check_banned(text)

    if not missing and not banned:
        print(f"PASS: {args.path} satisfies {args.mode} contract.")
        return 0

    if missing:
        print("Missing required signals:")
        for item in missing:
            print(f"- {item}")
    if banned:
        print("Banned phrases found:")
        for phrase in banned:
            print(f"- {phrase}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
