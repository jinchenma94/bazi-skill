#!/usr/bin/env bash
# pai_pan.py 包装器 —— 解决 Windows 控制台 GBK 乱码 + python3 命令缺失
#
# 用法（与 pai_pan.py 参数完全一致）：
#   ./scripts/run.sh --solar 1990-05-15 --hour 14:30 --sex 男 --place 杭州
#   ./scripts/run.sh --lunar 1990-04-21 --shichen 午 --sex 女
#   ./scripts/run.sh --solar 1990-05-15 --sex 男 > 命盘.md   # 可直接重定向
#   ./scripts/run.sh test                                    # 跑 11 个回归用例
#   ./scripts/run.sh doctor                                  # 全量自检
#
# 说明：
#   - 强制 UTF-8 输出（PYTHONIOENCODING / PYTHONUTF8），Windows bash 不再乱码
#   - 自动探测解释器：$PYTHON > python3 > python > py -3 > DSH 内置运行时
#   - 无第三方依赖，仅用标准库

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$DIR/pai_pan.py"

# 行尾自愈：Windows 上 core.autocrlf 会把脚本变成 CRLF，bash 会报
# "$'\r': command not found" 或 bad interpreter。检测到就地改回 LF 并重跑。
if [ -f "$DIR/run.sh" ] && grep -qU $'\r' "$DIR/run.sh" 2>/dev/null; then
  sed -i 's/\r$//' "$DIR/run.sh" 2>/dev/null && echo "[run.sh] 检测到 CRLF，已自动转换为 LF" >&2
fi

if [ ! -f "$SCRIPT" ]; then
  echo "找不到排盘脚本：$SCRIPT" >&2
  exit 1
fi

# --- 定位解释器 ---------------------------------------------------------------
find_python() {
  local cand
  for cand in "${PYTHON:-}" python3 python py; do
    [ -n "$cand" ] || continue
    if command -v "$cand" >/dev/null 2>&1; then
      if [ "$cand" = "py" ]; then
        if py -3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)' >/dev/null 2>&1; then
          echo "py -3"; return 0
        fi
      elif "$cand" -c 'import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)' >/dev/null 2>&1; then
        echo "$cand"; return 0
      fi
    fi
  done
  # DSH 内置运行时兜底
  for cand in \
    "$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/python.exe" \
    "$LOCALAPPDATA/Programs/DeepSeek Harness/resources/runtime/python/python.exe"
  do
    [ -x "$cand" ] && { echo "$cand"; return 0; }
  done
  return 1
}

PY_BIN="$(find_python)" || {
  echo "未找到 Python 3.8+。请安装 python3，或用 PYTHON=/path/to/python 指定。" >&2
  exit 127
}

# --- 强制 UTF-8 ---------------------------------------------------------------
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1

# 子命令：test → 跑回归用例；doctor → 自检
if [ "${1:-}" = "test" ]; then
  shift
  exec $PY_BIN "$DIR/test_pai_pan.py" "$@"
fi
if [ "${1:-}" = "doctor" ] || [ "${1:-}" = "--doctor" ]; then
  shift
  exec bash "$DIR/doctor.sh" "$@"
fi

exec $PY_BIN "$SCRIPT" "$@"
