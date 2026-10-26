#!/usr/bin/env bash
# bazi skill 自检 —— 在 UTF-8 / CRLF / 缺解释器 / 文件缺失 等情况下给出可定位的失败
#
# 用法：
#   ./scripts/doctor.sh          # 全量自检（跑 11 个回归用例）
#   ./scripts/doctor.sh --quick  # 跳过回归用例
#
# 退出码：0 全部通过；1 有 FAIL（技能不可用）；2 仅 WARN（可用但有风险）

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

FAILS=0
WARNS=0
ok()   { printf '  [OK]   %s\n' "$*"; }
warn() { printf '  [WARN] %s\n' "$*"; WARNS=$((WARNS+1)); }
bad()  { printf '  [FAIL] %s\n' "$*"; FAILS=$((FAILS+1)); }
info() { printf '  [INFO] %s\n' "$*"; }
sec()  { printf '\n== %s ==\n' "$*"; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------- 1. 文件完整性
sec "1/7 文件完整性"
for f in SKILL.md README.md scripts/pai_pan.py scripts/test_pai_pan.py scripts/run.sh \
         references/wuxing-tables.md references/shichen-table.md \
         references/dayun-rules.md references/shensha-table.md references/classical-texts.md; do
  if [ -s "$ROOT/$f" ]; then ok "$f"; else bad "缺失或为空：$f"; fi
done

# ---------------------------------------------------------------- 2. front matter
sec "2/7 SKILL.md front matter"
if [ -s "$ROOT/SKILL.md" ]; then
  head -1 "$ROOT/SKILL.md" | grep -q '^---$' && ok "以 --- 开头" || bad "front matter 未以 --- 开头（skill 不会被加载）"
  awk '/^---$/{n++; next} n==1{print}' "$ROOT/SKILL.md" > "$TMP/fm.yml"
  grep -q '^name:' "$TMP/fm.yml" && ok "有 name 字段" || bad "缺 name 字段"
  grep -q '^description:' "$TMP/fm.yml" && ok "有 description 字段" || bad "缺 description 字段"
  fmname="$(sed -n 's/^name:[[:space:]]*//p' "$TMP/fm.yml" | head -1 | tr -d '\r')"
  dirname_="$(basename "$ROOT")"
  if [ "$fmname" = "$dirname_" ]; then
    ok "name($fmname) 与目录名一致"
  else
    warn "name($fmname) 与目录名($dirname_) 不一致 —— 触发词可能失效"
  fi
  # 闭合 --- 必须出现在正文之前（≤60 行），否则整篇都会被当成 front matter
  close_line="$(awk 'NR>1 && /^---$/{print NR; exit}' "$ROOT/SKILL.md")"
  if [ -n "$close_line" ] && [ "$close_line" -le 60 ]; then
    ok "front matter 在第 $close_line 行闭合"
    # 头部区块内不应出现 Markdown 标题；出现即为闭合 --- 被误删、正文被吞进头部
    heading_in_fm="$(sed -n "2,$((close_line-1))p" "$ROOT/SKILL.md" | grep -c '^#')"
    if [ "$heading_in_fm" = "0" ]; then
      ok "头部区块内无 Markdown 标题（结构正常）"
    else
      bad "头部区块内含 $heading_in_fm 个 Markdown 标题 —— 闭合 --- 缺失/错位，描述会污染整篇"
    fi
  else
    bad "front matter 缺闭合 ---（或闭合位置异常：${close_line:-无}）—— skill 会整篇失效"
  fi
else
  bad "SKILL.md 不存在，跳过"
fi

# ---------------------------------------------------------------- 3. 行尾
sec "3/7 行尾（.sh 带 CRLF = bash 直接报 bad interpreter）"
# 用 coreutils 判定，不依赖 python：去掉 CR 后与原文件相同 → 纯 LF
has_cr() { ! cmp -s <(tr -d '\r' < "$1") "$1"; }
sh_bad=0; soft=0; soft_list=""
while IFS= read -r f; do
  rel="${f#"$ROOT"/}"
  has_cr "$f" || continue
  case "$rel" in
    *.sh) bad "含 CRLF（致命，bash 会崩）：$rel"; sh_bad=1 ;;
    *)    soft=$((soft+1)); soft_list="$soft_list $rel" ;;
  esac
done < <(find "$ROOT" -path "$ROOT/.git" -prune -o -type f \( -name '*.sh' -o -name '*.py' -o -name '*.md' \) -print)
if [ "$sh_bad" = "0" ] && [ "$soft" = "0" ]; then
  ok "所有 .sh/.py/.md 均为 LF"
elif [ "$sh_bad" = "0" ]; then
  info "$soft 个文本文件为 CRLF（不影响 Python/Markdown 运行）：$(echo "$soft_list" | cut -c1-60)…"
  info "如需归一：git config core.autocrlf false && git checkout -- ."
fi
if grep -q 'eol=lf' "$ROOT/.gitattributes" 2>/dev/null; then
  ok ".gitattributes 已锁 *.sh eol=lf（防 bash 脚本被转成 CRLF）"
else
  warn "缺 *.sh eol=lf 规则 —— 下次 checkout 可能把 run.sh 变成 CRLF"
fi

# ---------------------------------------------------------------- 4. 解释器
sec "4/7 Python 解释器"
PY=""
for cand in "${PYTHON:-}" python3 python py; do
  [ -n "$cand" ] || continue
  if [ "$cand" = "py" ]; then
    py -3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)' >/dev/null 2>&1 && { PY="py -3"; break; }
  else
    command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)' >/dev/null 2>&1 && { PY="$cand"; break; }
  fi
done
if [ -z "$PY" ]; then
  for cand in "$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/python.exe"; do
    [ -x "$cand" ] && { PY="$cand"; break; }
  done
fi
if [ -n "$PY" ]; then
  ok "$($PY -c 'import platform,sys;print(platform.python_implementation(), platform.python_version())') @ $PY"
else
  bad "未找到 Python 3.8+（排盘无法运行）"
fi

# ---------------------------------------------------------------- 5. 排盘输出
sec "5/7 排盘输出与编码"
if [ -n "$PY" ]; then
  export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
  "$PY" "$DIR/pai_pan.py" --solar 1990-05-15 --hour 12:00 --sex 男 --place 北京 > "$TMP/a.txt" 2>"$TMP/a.err"
  if [ -s "$TMP/a.txt" ]; then
    grep -q '## 四柱' "$TMP/a.txt" && ok "输出含 ## 四柱" || bad "输出缺 ## 四柱"
    grep -q '## 大运' "$TMP/a.txt" && ok "输出含 ## 大运" || bad "输出缺 ## 大运"
    grep -q '庚辰' "$TMP/a.txt" && ok "黄金值 庚辰 命中" || bad "黄金值 庚辰 未命中（排盘逻辑被改动？）"
    if "$PY" -c "
import sys,codecs
raw=open(sys.argv[1],'rb').read()
try:
    txt=raw.decode('utf-8')
except UnicodeDecodeError as e:
    print('NOT-UTF8',e); sys.exit(1)
print('U+FFFD' if '\ufffd' in txt else 'CLEAN')
" "$TMP/a.txt" | grep -q CLEAN; then
      ok "输出是合法 UTF-8 且无替换字符"
    else
      bad "输出不是干净 UTF-8（编码链路被破坏）"
    fi
    # 确定性
    "$PY" "$DIR/pai_pan.py" --solar 1990-05-15 --hour 12:00 --sex 男 --place 北京 > "$TMP/b.txt" 2>/dev/null
    cmp -s "$TMP/a.txt" "$TMP/b.txt" && ok "两次运行输出一致（确定性）" || bad "两次运行结果不同（非确定性）"
  else
    bad "排盘脚本无输出：$(head -2 "$TMP/a.err" | tr '\n' ' ')"
  fi
else
  bad "无解释器，跳过排盘检查"
fi

# ---------------------------------------------------------------- 6. 回归用例
sec "6/7 回归用例"
if [ "$QUICK" = "1" ]; then
  warn "--quick：跳过 11 个回归用例"
elif [ -n "$PY" ]; then
  # 跑两种环境：上游 bug（父进程按 locale 解码、子进程输出 UTF-8）只在
  # 设了 PYTHONIOENCODING=utf-8 而**没有** PYTHONUTF8 时暴露，所以必须单独跑一遍。
  export PYTHONDONTWRITEBYTECODE=1
  suite_ok=1
  (
    cd "$ROOT" || exit 1
    env -u PYTHONUTF8 PYTHONIOENCODING=utf-8 "$PY" scripts/test_pai_pan.py
  ) > "$TMP/t_utf8.txt" 2>&1 || true
  if grep -q '^OK$' "$TMP/t_utf8.txt"; then
    ok "UTF-8 环境：$(grep -E '^Ran ' "$TMP/t_utf8.txt" | head -1) → OK"
  else
    bad "UTF-8 环境用例失败：$(grep -E '^(FAILED|ERROR)' "$TMP/t_utf8.txt" | head -1)"
    suite_ok=0
  fi
  (
    cd "$ROOT" || exit 1
    env -u PYTHONUTF8 -u PYTHONIOENCODING "$PY" scripts/test_pai_pan.py
  ) > "$TMP/t_plain.txt" 2>&1 || true
  if grep -q '^OK$' "$TMP/t_plain.txt"; then
    ok "默认 locale 环境：$(grep -E '^Ran ' "$TMP/t_plain.txt" | head -1) → OK"
  else
    bad "默认 locale 环境用例失败：$(grep -E '^(FAILED|ERROR)' "$TMP/t_plain.txt" | head -1)"
    suite_ok=0
  fi
  [ "$suite_ok" = "0" ] && info "定位：对比 $TMP/t_utf8.txt 与 $TMP/t_plain.txt 的差异"
else
  bad "无解释器，跳过"
fi

# ---------------------------------------------------------------- 7. 安装形态
sec "7/7 安装形态"
case "$ROOT" in
  *"/.dsh/skills/"*)
    realroot="$(cd "$ROOT" && pwd -P)"
    if [ -r "$realroot/SKILL.md" ]; then
      ok "经 ~/.dsh/skills 链接加载，真实路径 $realroot"
    else
      bad "链接目标不可读：$realroot（junction 断了，重跑 mkdir/link）"
    fi ;;
  *"/.claude/skills/"*)
    ok "位于 ~/.claude/skills（Claude Code 全局）" ;;
  *)
    warn "非标准安装位置：$ROOT" ;;
esac
if [ -d "$HOME/.dsh/skills/bazi" ]; then ok "DSH 侧入口存在（~/.dsh/skills/bazi）"; else warn "缺 DSH 侧入口，本会话内可能加载不到该 skill"; fi
if command -v git >/dev/null 2>&1 && [ -d "$ROOT/.git" ]; then
  ok "git 仓库：$(git -C "$ROOT" log -1 --format='%h %s' 2>/dev/null | cut -c1-60)"
else
  warn "非 git 仓库（无法 git pull 更新）"
fi

# ---------------------------------------------------------------- 汇总
printf '\n== 汇总 ==\n'
printf '  FAIL=%d  WARN=%d\n' "$FAILS" "$WARNS"
if [ "$FAILS" -gt 0 ]; then echo "  结论：技能不可用，按上面 [FAIL] 逐条修"; exit 1; fi
if [ "$WARNS" -gt 0 ]; then echo "  结论：可用，但有风险项"; exit 2; fi
echo "  结论：全部通过"
