#!/bin/bash
#######################################################################
# CaMa-Flood 运行前置条件检查脚本
# 用途：自动检查所有必需文件和配置
#######################################################################

if [ $# -lt 1 ]; then
    echo "用法: $0 <流域名> [年份] [输出格式]"
    echo "示例: $0 bengbu 2024"
    echo "示例: $0 wangjiaba 2023 bin   # 降尺度时需要bin格式"
    exit 1
fi

BASIN=$1
YEAR=${2:-2024}
OUTPUT_FORMAT=${3:-nc}  # nc 或 bin
BASE="/Volumes/Expansion2t/hydro-model-workspace"

echo "========================================="
echo "🔍 CaMa-Flood 运行前置条件检查"
echo "========================================="
echo "流域: $BASIN"
echo "年份: $YEAR"
echo "输出格式: $OUTPUT_FORMAT"
echo ""

ERRORS=0
WARNINGS=0

# 🔴 易错点提醒
echo "🔴🔴🔴 易错点提醒 🔴🔴🔴"
echo "1. Python脚本必须先激活虚拟环境:"
echo "   source /Users/yc/Desktop/project/python_env/bin/activate"
echo "2. 河网地图必须按4步顺序准备，不能跳步"
echo "3. 降尺度需要Binary输出(LOUTCDF=.FALSE.)"
echo ""

# 1. 检查VIC输出
echo "📋 [1/6] 检查VIC输出..."
VIC_RESULT_DIR="$BASE/outputs/$BASIN/vic_result"
if [ -d "$VIC_RESULT_DIR" ]; then
    FILE_COUNT=$(ls "$VIC_RESULT_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "  ✅ VIC结果文件: $FILE_COUNT 个"
    else
        echo "  ❌ 错误: VIC结果目录为空"
        ERRORS=$((ERRORS+1))
    fi
else
    echo "  ❌ 错误: VIC结果目录不存在: $VIC_RESULT_DIR"
    ERRORS=$((ERRORS+1))
fi

# 2. 检查NetCDF径流文件
echo ""
echo "📋 [2/6] 检查NetCDF径流文件..."
RUNOFF_NC="$BASE/outputs/$BASIN/cama_input/runoff_$YEAR.nc"
if [ -f "$RUNOFF_NC" ]; then
    SIZE=$(du -h "$RUNOFF_NC" | cut -f1)
    echo "  ✅ NetCDF文件存在: $SIZE"
else
    echo "  ❌ 错误: NetCDF文件不存在: $RUNOFF_NC"
    ERRORS=$((ERRORS+1))
fi

# 3. 检查地图目录（关键）
echo ""
echo "📋 [3/6] 检查CaMa地图目录（🚨关键）..."
MAP_DIR="$BASE/model/cmf_v420_pkg/map/${BASIN}_15min"
if [ -d "$MAP_DIR" ]; then
    echo "  ✅ 地图目录存在: ${BASIN}_15min"

    # 检查关键地图文件
    REQUIRED_FILES="nextxy.bin ctmare.bin elevtn.bin nxtdst.bin rivlen.bin fldhgt.bin"
    MISSING_FILES=""
    for FILE in $REQUIRED_FILES; do
        if [ ! -f "$MAP_DIR/$FILE" ]; then
            MISSING_FILES="$MISSING_FILES $FILE"
        fi
    done

    if [ -z "$MISSING_FILES" ]; then
        echo "  ✅ 基础地图文件完整"
    else
        echo "  ❌ 错误: 缺少地图文件:$MISSING_FILES"
        echo "  💡 需要执行步骤1: cd $MAP_DIR/src_region && ./s01-regional_map.sh"
        ERRORS=$((ERRORS+1))
    fi
else
    echo "  ❌ 错误: 地图目录不存在: $MAP_DIR"
    echo "  💡 提示: 必须先创建目录并按顺序执行地图准备四步骤！"
    echo "  💡 步骤1: 编辑并运行 src_region/s01-regional_map.sh"
    echo "  💡 步骤2: 编辑并运行 src_param/s02-generate_inpmat.sh"
    echo "  💡 步骤3: 运行 src_param/s01-channel_params.sh"
    echo "  💡 步骤4: 配置运行脚本 gosh/run_${BASIN}_1d.sh"
    ERRORS=$((ERRORS+1))
fi

# 4. 检查河道参数文件
echo ""
echo "📋 [4/6] 检查河道参数文件..."
RIVER_FILES="rivwth.bin rivhgt.bin rivman.bin rivwth_gwdlr.bin"
MISSING_RIVER=""
for FILE in $RIVER_FILES; do
    if [ ! -f "$MAP_DIR/$FILE" ]; then
        MISSING_RIVER="$MISSING_RIVER $FILE"
    fi
done

if [ -z "$MISSING_RIVER" ]; then
    echo "  ✅ 河道参数文件完整"
else
    echo "  ❌ 错误: 缺少河道参数:$MISSING_RIVER"
    echo "  💡 提示: 执行步骤3生成河道参数（直接运行，不需要手动制作任何文件）:"
    echo "     cd $MAP_DIR/src_param && ./s01-channel_params.sh"
    echo "  🔴 注意: 不要手动复制或创建这些文件！必须用脚本自动生成"
    ERRORS=$((ERRORS+1))
fi

# 5. 检查输入矩阵文件
echo ""
echo "📋 [5/6] 检查输入矩阵文件..."
DIMINFO="$MAP_DIR/diminfo_${BASIN}_025deg.txt"
INPMAT="$MAP_DIR/inpmat_${BASIN}_025deg.bin"

if [ -f "$DIMINFO" ] && [ -f "$INPMAT" ]; then
    echo "  ✅ 输入矩阵文件存在"
else
    echo "  ❌ 错误: 输入矩阵文件缺失"
    [ ! -f "$DIMINFO" ] && echo "    - diminfo文件不存在"
    [ ! -f "$INPMAT" ] && echo "    - inpmat文件不存在"
    echo "  💡 提示: 执行步骤2生成输入矩阵:"
    echo "     cd $MAP_DIR/src_param && ./s02-generate_inpmat.sh"
    echo "  🔴 注意: 需要先编辑脚本中的VIC格网参数(GRSIZEIN, WESTIN等)"
    ERRORS=$((ERRORS+1))
fi

# 6. 检查1min高分辨率数据（用于降尺度）
echo ""
echo "📋 [6/6] 检查1min高分辨率数据（降尺度用）..."
HIRES_DIR="$MAP_DIR/1min"
if [ -d "$HIRES_DIR" ]; then
    FILE_COUNT=$(ls "$HIRES_DIR"/*.bin 2>/dev/null | wc -l | tr -d ' ')
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "  ✅ 1min数据存在: $FILE_COUNT 个文件"
    else
        echo "  ⚠️  警告: 1min目录为空（降尺度时需要）"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo "  ⚠️  警告: 1min目录不存在（降尺度时需要）"
    WARNINGS=$((WARNINGS+1))
fi

# 总结
echo ""
echo "========================================="
echo "📊 检查结果总结"
echo "========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ 全部检查通过！可以运行CaMa-Flood模拟"
    if [ "$OUTPUT_FORMAT" = "bin" ]; then
        echo ""
        echo "🔴 降尺度提醒: 确保运行脚本中 LOUTCDF = .FALSE."
    fi
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  有 $WARNINGS 个警告，但可以继续运行"
    echo "   （降尺度功能可能受影响）"
    exit 0
else
    echo "❌ 发现 $ERRORS 个错误，$WARNINGS 个警告"
    echo ""
    echo "🔧 河网地图准备四步骤（必须按顺序执行）:"
    echo ""
    echo "   步骤1: 地图准备"
    echo "          cd $BASE/model/cmf_v420_pkg/map/${BASIN}_15min/src_region"
    echo "          # 编辑 s01-regional_map.sh 的边界参数(WEST/EAST/SOUTH/NORTH)"
    echo "          ./s01-regional_map.sh"
    echo ""
    echo "   步骤2: 生成输入矩阵"
    echo "          cd $BASE/model/cmf_v420_pkg/map/${BASIN}_15min/src_param"
    echo "          # 编辑 s02-generate_inpmat.sh 的VIC格网参数"
    echo "          ./s02-generate_inpmat.sh"
    echo ""
    echo "   步骤3: 生成河道参数（🔴直接运行，不要手动制作文件）"
    echo "          cd $BASE/model/cmf_v420_pkg/map/${BASIN}_15min/src_param"
    echo "          ./s01-channel_params.sh"
    echo ""
    echo "   步骤4: 配置并运行"
    echo "          cd $BASE/model/cmf_v420_pkg/gosh"
    echo "          # 编辑 run_${BASIN}_1d.sh"
    echo "          ./run_${BASIN}_1d.sh"
    echo ""
    echo "🔴 降尺度额外要求:"
    echo "   - 运行脚本中必须设置 LOUTCDF = .FALSE. (Binary输出)"
    echo "   - 输出bin文件后才能进行降尺度处理"
    exit 1
fi
