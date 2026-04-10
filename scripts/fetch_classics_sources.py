#!/usr/bin/env python3
"""Fetch lightweight metadata for public Bazi classics source pages.

This maintenance helper intentionally avoids storing full book text. It writes
small JSON metadata records that can be used to verify URLs before a maintainer
manually distills methods into references/masters-lineage.md.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path


USER_AGENT = "xuan-skill-source-check/1.0"


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    figures: tuple[str, ...]
    url: str
    status: str
    boundary: str
    fetch_allowed: bool


SOURCES: tuple[Source, ...] = (
    Source(
        key="sanming-tonghui-wikisource",
        title="三命通会",
        figures=("万民英",),
        url="https://zh.wikisource.org/zh-hans/%E4%B8%89%E5%91%BD%E9%80%9A%E6%9C%83",
        status="public-domain-page",
        boundary="Use for source verification and method distillation; do not copy long text.",
        fetch_allowed=True,
    ),
    Source(
        key="sanming-tonghui-siku-wikisource",
        title="三命通会（四库全书本）",
        figures=("万民英",),
        url="https://zh.wikisource.org/zh-hant/%E4%B8%89%E5%91%BD%E9%80%9A%E6%9C%83_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29",
        status="public-domain-page",
        boundary="Use as a variant/source cross-check; do not copy long text.",
        fetch_allowed=True,
    ),
    Source(
        key="yuanhai-ziping-wikisource",
        title="渊海子平",
        figures=("徐子平", "徐大升"),
        url="https://zh.wikisource.org/zh-hans/%E6%B7%B5%E6%B5%B7%E5%AD%90%E5%B9%B3",
        status="public-domain-page",
        boundary="Use for terminology and method cross-checking; attribution may need care.",
        fetch_allowed=True,
    ),
    Source(
        key="ditiansui-wikisource",
        title="滴天髓",
        figures=("任铁樵",),
        url="https://zh.wikisource.org/zh-hans/%E6%BB%B4%E5%A4%A9%E9%AB%93",
        status="public-domain-page",
        boundary="Use text-level concepts; verify commentary attribution separately.",
        fetch_allowed=True,
    ),
    Source(
        key="shenfeng-tongkao-wikisource",
        title="神峰通考",
        figures=("张楠",),
        url="https://zh.wikisource.org/zh-hans/%E7%A5%9E%E5%B3%B0%E9%80%9A%E8%80%83",
        status="public-domain-page",
        boundary="Use for disease-remedy and pattern examples; do not copy long text.",
        fetch_allowed=True,
    ),
    Source(
        key="sanming-tonghui-ctext",
        title="三命通会（中国哲学书电子化计划）",
        figures=("万民英",),
        url="https://ctext.org/wiki.pl?if=gb&remap=gb&res=587236",
        status="public-domain-page",
        boundary="Use as a source cross-check; respect site terms and avoid bulk scraping.",
        fetch_allowed=True,
    ),
    Source(
        key="modern-bibliography-only",
        title="近现代命理书目",
        figures=("韦千里", "袁树珊", "徐乐吾"),
        url="",
        status="bibliography-only",
        boundary="Do not fetch full text. Record bibliographic facts and manually distill methods.",
        fetch_allowed=False,
    ),
)


class TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._in_h1 = False
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "h1":
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        if tag.lower() == "h1":
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)

    @property
    def title(self) -> str:
        return normalize_text(" ".join(self.title_parts))

    @property
    def h1(self) -> str:
        return normalize_text(" ".join(self.h1_parts))


def normalize_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def fetch_metadata(source: Source, timeout: int) -> dict[str, object]:
    if not source.fetch_allowed or not source.url:
        return {
            **asdict(source),
            "fetched": False,
            "reason": "fetch not allowed for this source",
        }

    request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(512_000)
            content_type = response.headers.get("content-type", "")
            charset = response.headers.get_content_charset() or "utf-8"
    except urllib.error.URLError as exc:
        return {
            **asdict(source),
            "fetched": False,
            "error": str(exc),
        }

    text = raw.decode(charset, errors="replace")
    parser = TitleParser()
    parser.feed(text)
    return {
        **asdict(source),
        "fetched": True,
        "content_type": content_type,
        "bytes_sampled": len(raw),
        "page_title": parser.title,
        "page_h1": parser.h1,
    }


def write_jsonl(records: list[dict[str, object]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "masters-source-check.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Print configured sources as JSON.")
    parser.add_argument("--fetch", action="store_true", help="Fetch lightweight metadata for allowed sources.")
    parser.add_argument(
        "--output-dir",
        default="tmp/masters-source-cache",
        help="Directory for JSONL metadata output when --fetch is used.",
    )
    parser.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    records = [asdict(source) for source in SOURCES]

    if args.list or not args.fetch:
        print(json.dumps(records, ensure_ascii=False, indent=2))

    if args.fetch:
        fetched = [fetch_metadata(source, args.timeout) for source in SOURCES]
        output = write_jsonl(fetched, Path(args.output_dir))
        print(f"Wrote {len(fetched)} source records to {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
