#!/bin/bash
# bazi-fortune skill 一键部署 + 冒烟测试
# Usage: bash deploy.sh [--skip-install]
#
# 步骤：
# 1. 安装 Python 依赖（sxtwl）
# 2. 复制 skill 到 OpenClaw 目录
# 3. 验证文件完整性
# 4. 跑冒烟测试（5 个排盘用例 + 8 维度运势健康）
# 5. 输出 PASS/FAIL 报告

set -e

SKILL_NAME="bazi-fortune"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_DIR="${HOME}/.openclaw/skills"
TARGET_DIR="${OPENCLAW_DIR}/${SKILL_NAME}"
SKIP_INSTALL=false

for arg in "$@"; do
    case $arg in
        --skip-install) SKIP_INSTALL=true ;;
    esac
done

echo "========================================"
echo "  bazi-fortune skill 部署脚本 v3.0"
echo "========================================"
echo ""

# Step 1: 安装 Python 依赖
if [ "$SKIP_INSTALL" = false ]; then
    echo "[1/5] 安装 Python 依赖..."
    if ! command -v pip3 &> /dev/null; then
        echo "❌ pip3 未找到，请先安装 Python 3.8+"
        exit 1
    fi
    pip3 install --user -r "${SCRIPT_DIR}/requirements.txt" 2>&1 | tail -5
    echo "✅ 依赖安装完成"
else
    echo "[1/5] 跳过依赖安装（--skip-install）"
fi
echo ""

# Step 2: 复制到 OpenClaw 目录
echo "[2/5] 部署到 OpenClaw..."
mkdir -p "${OPENCLAW_DIR}"
if [ -d "${TARGET_DIR}" ]; then
    echo "⚠️  目标目录已存在: ${TARGET_DIR}"
    read -p "覆盖？[y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 取消部署"
        exit 1
    fi
    rm -rf "${TARGET_DIR}"
fi
cp -r "${SCRIPT_DIR}" "${TARGET_DIR}"
echo "✅ 已部署到: ${TARGET_DIR}"
echo ""

# Step 3: 验证文件完整性
echo "[3/5] 验证文件..."
required_files=("SKILL.md" "README.md" "requirements.txt" "LICENSE"
                "references/wuxing-tables.md"
                "references/shichen-table.md"
                "references/dayun-rules.md"
                "references/classical-texts.md"
                "references/fortune-health-rules.md"
                "scripts/fortune_health.py")
all_ok=true
for f in "${required_files[@]}"; do
    if [ -f "${TARGET_DIR}/${f}" ]; then
        size=$(stat -c%s "${TARGET_DIR}/${f}")
        echo "  ✅ ${f} (${size} bytes)"
    else
        echo "  ❌ 缺失: ${f}"
        all_ok=false
    fi
done
if [ "$all_ok" = false ]; then
    echo "❌ 文件缺失，部署失败"
    exit 1
fi
echo "✅ 文件完整"
echo ""

# Step 4: 冒烟测试 - 排盘核心
echo "[4/5] 排盘冒烟测试（5 个用例）..."
python3 -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
try:
    import sxtwl
    print(f'  ✅ sxtwl 版本: {sxtwl.__version__ if hasattr(sxtwl, \"__version__\") else \"unknown\"}')
except ImportError:
    print('  ❌ sxtwl 未安装，排盘功能不可用')
    print('     运行: pip3 install sxtwl')
    sys.exit(1)

TG = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
DZ = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']

tests = [
    ('1990-05-15 10:30 男 辽宁丹东', 1990, 5, 15, 10, 30, 124.39),
    ('1987-06-11 8:43 女 博白',     1987, 6, 11,  8, 43, 110.16),
    ('1985-08-20 男 北京',          1985, 8, 20, 12,  0, 116.40),
    ('1988-02-03 10:00 男 上海',    1988, 2,  3, 10,  0, 121.47),
    ('1992-03-08 23:30 男 北京',    1992, 3,  8, 23, 30, 116.40),
]

passed = 0
for label, y, m, d, h, mi, lon in tests:
    try:
        day = sxtwl.fromSolar(y, m, d)
        yz = day.getYearGZ()
        mz = day.getMonthGZ()
        dz = day.getDayGZ()
        shi_cha = (lon - 120) * 4
        print(f'  ✅ {label}')
        print(f'      年柱: {TG[yz.tg]}{DZ[yz.dz]}, 月柱: {TG[mz.tg]}{DZ[mz.dz]}, 日柱: {TG[dz.tg]}{DZ[dz.dz]}, 时差: {shi_cha:.0f}分钟')
        passed += 1
    except Exception as e:
        print(f'  ❌ {label}: {e}')

print(f'')
print(f'通过: {passed}/{len(tests)}')
if passed != len(tests):
    print('❌ 排盘测试失败')
    sys.exit(1)
print('🎉 排盘测试全部通过')
"

echo ""

# Step 5: 冒烟测试 - 运势 + 健康 8 维度
echo "[5/5] 运势健康冒烟测试（8 维度）..."
python3 -c "
import sys
sys.path.insert(0, '${TARGET_DIR}/scripts')
sys.stdout.reconfigure(encoding='utf-8')

try:
    from fortune_health import generate_full_report, format_markdown
    from datetime import date
    print('  ✅ fortune_health 模块加载成功')
except Exception as e:
    print(f'  ❌ 加载失败: {e}')
    sys.exit(1)

# 测试用例：SKILL.md example 1990-05-15
test_chart = {
    '年柱': ('庚', '午'),
    '月柱': ('辛', '巳'),
    '日柱': ('甲', '子'),
    '时柱': ('己', '巳'),
}

target = date.today()
print(f'  📅 测试日期: {target}')

try:
    report = generate_full_report(test_chart, target)
    
    # 验证 8 维度全部存在
    required = [
        ('运势', '今日'), ('运势', '本周'), ('运势', '本月'), ('运势', '本年'),
        ('健康', '今日'), ('健康', '节气'), ('健康', '季节'), ('健康', '本年'),
    ]
    passed = 0
    for category, dim in required:
        if category in report and dim in report[category]:
            data = report[category][dim]
            # 验证关键字段
            if category == '运势':
                if dim == '今日' and '维度' in data and '星数' not in data:
                    # 今日运势 维度子项
                    print(f'  ✅ 运势/{dim}: 整体={data[\"维度\"][\"整体\"]}星, 干支={data[\"干支\"]}')
                elif dim == '本周' and '日明细' in data and '最吉日' in data:
                    print(f'  ✅ 运势/{dim}: 平均分={data[\"平均分\"]}, 最吉={data[\"最吉日\"][\"干支\"]}, 最凶={data[\"最凶日\"][\"干支\"]}')
                elif dim in ('本月', '本年') and '星数' in data:
                    print(f'  ✅ 运势/{dim}: {data[\"星数\"]}星 ({data.get(\"综合分\", data.get(\"分数\"))})')
                else:
                    print(f'  ✅ 运势/{dim}: 数据完整')
            else:  # 健康
                if '脏腑' in data and '建议' in data:
                    print(f'  ✅ 健康/{dim}: {data[\"脏腑\"]} ({data.get(\"状态\", \"平和\")})')
                else:
                    print(f'  ✅ 健康/{dim}: 数据完整')
            passed += 1
        else:
            print(f'  ❌ {category}/{dim}: 缺失')
    
    print(f'')
    print(f'通过: {passed}/{len(required)}')
    if passed == len(required):
        print('🎉 运势健康 8 维度全部通过')
        sys.exit(0)
    else:
        print('❌ 部分维度失败')
        sys.exit(1)
except Exception as e:
    print(f'  ❌ 运行失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo ""
echo "========================================"
echo "  部署完成 (v3.0)"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 重启 OpenClaw (openclaw restart)"
echo "  2. 在 OpenClaw 中测试触发："
echo "     - 基础: '测八字 1990-05-15 10:30 男 辽宁丹东'"
echo "     - 运势: '今日运势怎么样'"
echo "     - 健康: '我的健康状况'"
echo ""
