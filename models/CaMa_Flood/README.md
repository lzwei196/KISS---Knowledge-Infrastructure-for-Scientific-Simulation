---
name: cama-flood-integration
description: VIC-CaMa-Flood模型耦合助手。用于将VIC水文模型输出与CaMa-Flood汇流模型耦合，包括区域化、数据转换和模型运行
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
---

> **MANDATORY EXECUTION POLICY** — READ BEFORE PROCEEDING
>
> You MUST run the **actual model binary or package** described in this document.
> If the model fails to import, compile, or execute, you MUST:
> 1. Check `diagnostics/triplets.yaml` for a matching error pattern
> 2. Try the fix suggested in the triplet's `remedy` section
> 3. If still failing, report the error to the user with full details
>
> You MUST NOT substitute a simplified Python formula, regression equation,
> or hand-coded approximation in place of the real model. Doing so produces
> scientifically invalid results and defeats the purpose of the KI.
>
> Before starting, run: `python preflight_check.py` (in this KI directory)
> to verify that the model binary/package and required data are available.

---



# VIC-CaMa-Flood模型耦合助手

你是一个专业的水文模型耦合助手，帮助用户将VIC模型输出与CaMa-Flood汇流模型集成。

## CaMa-Flood模型简介

CaMa-Flood (Catchment-based Macro-scale Floodplain) 是一个全球尺度的河道汇流和洪水演算模型，用于模拟河流水位、流量和洪水淹没范围。

### 模型特点
- 基于流域单元的汇流模型
- 可模拟河道水流和洪泛区淹没
- 支持多分辨率（15min, 3sec, 1min等）
- 可与陆面模型（VIC, MATSIRO等）耦合

## 模型耦合流程

```
VIC模型输出 → 数据格式转换 → CaMa-Flood地图准备(3步骤) → CaMa-Flood运行 → 流量/水位输出

步骤1: VIC运行
  └─ 输出: huaihe_fluxes_*.txt (格点文本文件)
  └─ 变量: OUT_RUNOFF, OUT_BASEFLOW

步骤2: VIC后处理
  └─ 脚本: scripts/vic_post/process_data_windows_ymd.py
  └─ 输出: runoff_YYYY.nc (NetCDF格式)
  └─ 位置: outputs/{basin}/cama_input/

步骤3: CaMa-Flood地图准备（⚠️ 必须执行）
  ├─ 3.1 区域化：从全球地图裁剪流域
  │   └─ 工具: src_region/cut_domain, combine_hires
  ├─ 3.2 生成输入矩阵：VIC网格→CaMa网格映射
  │   └─ 工具: src_param/generate_inpmat
  └─ 3.3 生成河道参数：基于径流气候态
      └─ 工具: src_param/calc_outclm, calc_rivwth

步骤4: CaMa-Flood运行
  ├─ NC格式: 完整变量输出（outflw, rivdph, sfcelv, flddph, fldfrc, rivsto）
  └─ BIN格式: 仅flddph输出（用于降尺度）
```

## 工作空间结构

```
hydro-model-workspace/
├── outputs/vic_result/         # VIC模型输出
│   └── huaihe_fluxes_*.txt     # 224个格点文件
├── scripts/vic_post/           # VIC后处理脚本
│   └── process_data_windows_ymd.py
└── model/cmf_v420_pkg/         # CaMa-Flood模型
    ├── src/                    # 源代码
    │   └── MAIN_cmf            # 可执行文件 (已编译)
    ├── map/                    # 地图文件
    │   ├── glb_15min/          # 全球15分地图
    │   ├── huaihe_15min/       # 淮河区域地图
    │   └── bengbu_15min/       # 蚌埠区域地图 (待生成)
    ├── inp/                    # 输入数据
    │   └── bengbu/             # 蚌埠径流输入 (待生成)
    ├── out/                    # 输出结果
    │   └── bengbu_*/           # 蚌埠模拟结果
    └── gosh/                   # 运行脚本
        └── run_bengbu_1d.sh    # 蚌埠运行脚本 (待创建)
```

## 关键配置参数

### 流域边界 (bengbu)

根据shapefile自动获取：
- **West**: 111.75° (向西扩展0.25°对齐网格)
- **East**: 117.75° (向东扩展0.25°对齐网格)
- **South**: 31.0°
- **North**: 35.0°
- **Grid Size**: 0.25° (与VIC一致)

### 网格维度

- **NX** (东西向): 24 格点 ((117.75-111.75)/0.25)
- **NY** (南北向): 16 格点 ((35.0-31.0)/0.25)
- **Total**: 384 格点 (覆盖区域，包含流域外)

### 时间配置

- **模拟时段**: 2023-01-01 至 2024-12-31
- **时间步长**: 86400秒 (日尺度)
- **输入频率**: 24小时 (IFRQ_INP = 24)
- **输出频率**: 24小时 (IFRQ_OUT = 24)

## ⚠️ 关键前置要求

### 必须完成VIC模拟
运行CaMa-Flood之前，必须先完成VIC模拟并生成NetCDF格式的径流数据。参见`vic-auto-run` skill。

### ⚠️ 必须重新制作地图（不可复用）**【关键步骤】**

**🚨 严重警告**: 每个新流域都**必须**重新执行完整的地图准备三步骤，**绝对不能**直接使用map目录下已存在的文件夹（如manual_bengbu等）。

**为什么不能复用**:
- 不同流域的经纬度范围不同
- 河网拓扑结构不同
- VIC网格与CaMa网格的映射关系不同
- 直接复用会导致路径错误和模拟失败

**正确流程**:
1. **创建新目录**: `mkdir map/{basin}_15min/`（不是manual_{basin}）
2. **执行三步骤**: 区域化 → 输入矩阵 → 河道参数
3. **验证文件**: 确保所有.bin文件和diminfo文件已生成
4. **使用正确路径**: 运行脚本中使用 `map/{basin}_15min/` 而不是 `map/manual_{basin}/`

## 核心任务

### 任务0: 创建新的地图目录（⚠️ 必须执行）

**目的**: 为新流域创建专属的地图参数文件夹。

```bash
cd /Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map
mkdir {basin}_15min
```

**示例**: 对于蚌埠流域，创建`bengbu_15min`目录。

### 任务1: VIC输出后处理

**脚本**: `scripts/vic_post/process_{basin}.py`（每个流域一个脚本，如process_bengbu.py）

**功能**:
- 读取VIC格点文本文件 (huaihe_fluxes_*.txt)
- 提取径流数据 (OUT_RUNOFF + OUT_BASEFLOW)
- 转换为CaMa-Flood NetCDF格式

**🔴 关键修改**:
```python
# 输入路径 - 必须指向正确的流域VIC输出目录
INPUT_DIR = "/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/vic_result"

# 输出路径 - 统一放在流域的cama_input目录
OUTPUT_DIR = "/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_input"

# 时间范围
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"

# 网格定义 (根据流域调整)
NX = 24
NY = 16
WEST = 111.875   # 第一个格点中心经度
EAST = 117.625   # 最后一个格点中心经度
NORTH = 34.875   # 第一个格点中心纬度
SOUTH = 31.125   # 最后一个格点中心纬度
GRID_SIZE = 0.25

# 文件名前缀
FILE_PREFIX = "huaihe_fluxes_"
OUTPUT_NC_PREFIX = "{basin}_runoff_1d_"  # 🔴 输出文件名格式: {basin}_runoff_1d_YYYY.nc
```

**🔴 输出文件命名**: `{basin}_runoff_1d_YYYY.nc`（如`bengbu_runoff_1d_2024.nc`），CaMa运行脚本中的CROFCDF路径必须与此一致

### 任务2: CaMa-Flood地图准备（三步骤流程）

**⚠️ 关键**: 这三个步骤必须按顺序完成，每个新流域都必须重新执行。

#### 步骤2.1: 区域化（裁剪全球地图）

**目录**: `model/cmf_v420_pkg/map/{basin}_15min/src_region/`

**步骤**:

1. **复制区域化工具**:
   ```bash
   cd model/cmf_v420_pkg/map/{basin}_15min
   cp -r ../huaihe_15min/src_region ./src_region
   cd src_region
   ```

2. **🔴 编译区域化程序**（跨平台必须执行）:
   ```bash
   make clean
   make all
   ```
   **注意**: 二进制文件是平台相关的，从其他目录复制的.exe无法直接运行，必须重新编译

3. **创建s01-regional_map.sh** (根据流域修改经纬度范围):
   ```bash
   #!/bin/sh

   # 修改以下参数为实际流域范围
   SOURCE="../../glb_15min/"
   WEST="111.75"   # 西边界(度)
   EAST="117.75"   # 东边界(度)
   SOUTH="31.0"    # 南边界(度)
   NORTH="35.0"    # 北边界(度)

   echo "$SOURCE" > region_info.txt
   echo "$WEST" >> region_info.txt
   echo "$EAST" >> region_info.txt
   echo "$SOUTH" >> region_info.txt
   echo "$NORTH" >> region_info.txt

   ./cut_domain
   ./cut_bifway
   ./set_map

   # 生成高分辨率数据（用于降尺度）
   HDIRS="1min 30sec 15sec 3sec"
   for HIRES in $HDIRS
   do
     if [ -f $SOURCE/$HIRES/location.txt ]; then
       echo "处理高分辨率数据: $HIRES"
       mkdir -p ../$HIRES
       ./combine_hires $HIRES
     fi
   done

   ./s02-wrte_ctl_map.sh
   ```

4. **运行区域化**:
   ```bash
   chmod +x s01-regional_map.sh
   ./s01-regional_map.sh
   ```

**输出文件** (生成在 `../{basin}_15min/`):
- nextxy.bin - 流向数据
- ctmare.bin - 集水面积
- elevtn.bin - 高程
- nxtdst.bin - 到下游格点的距离
- rivlen.bin - 河道长度
- fldhgt.bin - 洪泛区高度
- width.bin - 默认河道宽度
- 1min/ - 高分辨率数据（用于降尺度）

#### 步骤2.2: 生成输入矩阵（VIC→CaMa映射）

**⚠️ 依赖**: 必须先完成步骤2.1（区域化）

**目录**: `model/cmf_v420_pkg/map/{basin}_15min/src_param/`

**步骤**:

1. **复制src_param工具**:
   ```bash
   cd model/cmf_v420_pkg/map/{basin}_15min
   cp -r ../glb_15min/src_param ./src_param
   cd src_param
   ```

2. **🔴 编译**（跨平台必须执行）:
   ```bash
   make clean
   make all
   ```
   **注意**: 必须在本机重新编译，不能使用其他平台编译的二进制文件

3. **创建s02-generate_inpmat.sh** (根据VIC网格修改参数):
   ```bash
   #!/bin/sh
   cd ..

   # 配置参数（根据实际VIC网格修改）
   DIMINFO="diminfo_{basin}_025deg.txt"
   INPMAT="inpmat_{basin}_025deg.bin"

   # VIC径流数据网格信息
   GRSIZEIN=0.25       # VIC网格大小
   WESTIN=111.75       # VIC域西边界
   EASTIN=117.75       # VIC域东边界
   NORTHIN=35.0        # VIC域北边界
   SOUTHIN=31.0        # VIC域南边界
   OLAT="NtoS"         # 纬度顺序：北到南

   TAG="1min"          # 高分辨率数据目录

   # 生成输入矩阵
   ./src_param/generate_inpmat $TAG $GRSIZEIN $WESTIN $EASTIN $NORTHIN $SOUTHIN $OLAT $DIMINFO $INPMAT
   ```

4. **运行**:
   ```bash
   chmod +x s02-generate_inpmat.sh
   ./s02-generate_inpmat.sh
   ```

**输出文件**:
- diminfo_{basin}_025deg.txt - 网格维度信息
- inpmat_{basin}_025deg.bin - 输入映射矩阵

#### 步骤2.3: 生成河道参数

**⚠️ 依赖**: 必须先完成步骤2.1和2.2

**⚠️ 重要**: 必须使用正确的径流气候态数据路径：
`/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map/data/ELSE_GPCC_coastmod_dayclm-1981-2010.one`

**目录**: `model/cmf_v420_pkg/map/{basin}_15min/src_param/`

**步骤**:

1. **创建s01-channel_params.sh**:
   ```bash
   #!/bin/sh
   cd ..

   TYPE='bin'
   INTERP='inpmat'
   DIMINFO='./diminfo_{basin}_025deg.txt'
   CROFBIN="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map/data/ELSE_GPCC_coastmod_dayclm-1981-2010.one"

   # 计算年平均流量
   ./src_param/calc_outclm $TYPE $INTERP $DIMINFO $CROFBIN

   # 河道参数
   HC=0.1; HP=0.50; HO=0.00; HMIN=1.0
   WC=2.50; WP=0.60; WO=0.00; WMIN=5.0

   # 计算河道宽度和深度
   ./src_param/calc_rivwth $TYPE $DIMINFO $HC $HP $HO $HMIN $WC $WP $WO $WMIN

   # 生成GWDLR和糙率
   cp rivwth.bin rivwth_gwdlr.bin
   python3 -c "
   import numpy as np
   data = np.fromfile('rivwth.bin', dtype='float32')
   data[:] = 0.03
   data.tofile('rivman.bin')
   "
   ```

2. **运行**:
   ```bash
   chmod +x s01-channel_params.sh
   ./s01-channel_params.sh
   ```

**输出文件**:
- rivwth.bin, rivhgt.bin - 河道宽度和深度
- rivwth_gwdlr.bin - GWDLR河宽
- rivman.bin - 河道糙率(默认0.03)

### 任务3: 创建CaMa-Flood运行脚本

**⚠️ 关键差异**:
- **NC格式**: 用于常规分析，输出多个变量（outflw, rivdph, sfcelv, flddph等）
- **BIN格式**: 仅用于降尺度，只输出flddph变量

**⚠️ 路径注意**: 必须使用绝对路径，避免使用`../`相对路径（会导致STOP 10错误）

**⚠️ LINTERP设置**:
- 如果VIC网格与CaMa网格完全匹配，设置`LINTERP=.FALSE.`和`CINPMAT=''`
- 如果需要插值映射，设置`LINTERP=.TRUE.`和`CINPMAT='...inpmat_{basin}_025deg.bin'`
- **推荐**: 使用`LINTERP=.FALSE.`（更稳定，避免插值错误）

#### 3.1 NC格式运行脚本

**文件**: `model/cmf_v420_pkg/gosh/run_{basin}_nc.sh`

**配置**:

```bash
#!/bin/sh

# --- 1. 基本设置 ---
BASE="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg"
export OMP_NUM_THREADS=8
cd ${BASE}

# --- 2. 实验定义 ---
EXP="bengbu_2024_nc"
RDIR="/Volumes/Expansion2t/hydro-model-workspace/outputs/bengbu/cama_nc"
PROG=${BASE}/src/MAIN_cmf
NMLIST="./input_cmf.nam"

YSTA=2023
YEND=2024
SPINUP=0
NSP=1  # Spin-up 次数

# --- 3. 准备运行目录 ---
mkdir -p ${RDIR}
cd ${RDIR}

if [ ${SPINUP} -eq 0 ]; then
  echo "--- New run, cleaning directory: ${RDIR} ---"
  rm -rf ./*
else
  NSP=0
fi

# --- 4. 年度循环 ---
ISP=1
IYR=${YSTA}
while [ ${IYR} -le ${YEND} ];
do
  echo ""
  echo "##################################################"
  echo "--- Processing Year: ${IYR} (Spin-up: ${ISP}) ---"
  echo "##################################################"

  CYR=`printf %04d ${IYR}`
  EYR=`expr ${IYR} + 1`

  if [ ${IYR} -eq ${YSTA} ] && [ ${SPINUP} -eq 0 ]; then
    LRESTART=".FALSE."
    CRESTSTO="''"
  else
    LRESTART=".TRUE."
    CRESTSTO="'./restart${CYR}010100.nc'"
  fi

  ln -sf $PROG ./MAIN_cmf

  # --- 5. 创建当年的配置文件 ---
  cat > ${NMLIST} << EOF
  &NRUNVER
  LADPSTP  = .TRUE.
  LPTHOUT  = .FALSE.
  LRESTART = ${LRESTART}
  /
  &NDIMTIME
  CDIMINFO = '../../map/bengbu_15min/diminfo_bengbu_025deg.txt'
  DT       = 86400
  IFRQ_INP = 24
  /
  &NPARAM
  PMANRIV  = 0.03D0
  PMANFLD  = 0.10D0
  PCADP    = 0.7
  PDSTMTH  = 10000.D0
  /
  &NSIMTIME
  SYEAR = ${IYR}
  SMON  = 1
  SDAY  = 1
  SHOUR = 0
  EYEAR = ${EYR}
  EMON  = 1
  EDAY  = 1
  EHOUR = 0
  /
  &NMAP
  LMAPCDF  = .FALSE.
  CNEXTXY  = '../../map/bengbu_15min/nextxy.bin'
  CGRAREA  = '../../map/bengbu_15min/ctmare.bin'
  CELEVTN  = '../../map/bengbu_15min/elevtn.bin'
  CNXTDST  = '../../map/bengbu_15min/nxtdst.bin'
  CRIVLEN  = '../../map/bengbu_15min/rivlen.bin'
  CFLDHGT  = '../../map/bengbu_15min/fldhgt.bin'
  CRIVWTH  = '../../map/bengbu_15min/rivwth_gwdlr.bin'
  CRIVHGT  = '../../map/bengbu_15min/rivhgt.bin'
  CRIVMAN  = '../../map/bengbu_15min/rivman.bin'
  /
  &NRESTART
  CRESTSTO = ${CRESTSTO}
  CRESTDIR = './'
  CVNREST  = 'restart'
  LRESTCDF = .TRUE.
  IFRQ_RST = 0
  /
  &NFORCE
  LINPCDF  = .TRUE.
  LINTERP  = .TRUE.
  CINPMAT  = '../../map/bengbu_15min/inpmat_bengbu_025deg.bin'
  CROFCDF  = '/Volumes/Expansion2t/hydro-model-workspace/outputs/bengbu/cama_input/bengbu_runoff_1d_${CYR}.nc'
  CVNROF   = 'Runoff'
  SYEARIN  = ${IYR}
  SMONIN   = 1
  SDAYIN   = 1
  SHOURIN  = 0
  /
  &NOUTPUT
  COUTDIR  = './'
  CVARSOUT = 'outflw,rivdph,sfcelv,flddph,fldfrc,rivsto'
  COUTTAG  = '${CYR}'
  LOUTCDF  = .TRUE.
  NDLEVEL  = 0
  IFRQ_OUT = 24
  /
  &NBOUND
  /
  &NDAMOUT
  /
  &NLEVEE
  /
EOF

  # --- 6. 执行模型 ---
  echo "Running CaMa-Flood for year ${IYR}..."
  time ./MAIN_cmf

  # --- 7. Spin-up 处理 ---
  if [ ${IYR} -eq ${YSTA} ] && [ ${ISP} -le ${NSP} ]; then
    SPINUP=1
    IYR1=`expr ${IYR} + 1`
    CYR1=`printf %04d ${IYR1}`
    mv ./restart${CYR1}010100.nc ./restart${CYR}010100.nc 2>/dev/null
    mkdir -p spinup-${ISP}
    mv ./*${CYR}.nc spinup-${ISP}/ 2>/dev/null
    ISP=`expr ${ISP} + 1`
  else
    IYR=`expr ${IYR} + 1`
  fi
done

echo "--- All simulations finished! ---"
echo "Results saved in: ${RDIR}"
```

**关键配置**:
- `LINTERP = .FALSE.` - 不使用插值（推荐，更稳定）
- `CINPMAT = ''` - 不使用输入矩阵
- `CROFCDF` - 使用**绝对路径**
- `CVARSOUT` - NC格式输出多个变量

#### 3.2 BIN格式运行脚本（用于降尺度）

**文件**: `model/cmf_v420_pkg/gosh/run_{basin}_bin.sh`

**差异**: 只需修改两处
1. `LOUTCDF = .FALSE.` - 输出BIN格式
2. `CVARSOUT = 'flddph'` - 只输出洪水淹没深度

```bash
#!/bin/sh

BASE="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg"
export OMP_NUM_THREADS=8

EXP="{basin}_YYYY_bin"
RDIR="/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_bin"
# ... (其他配置同NC格式) ...

cat > ${NMLIST} << EOFN
  # ... (前面配置同NC格式) ...
  &NOUTPUT
  COUTDIR  = './'
  CVARSOUT = 'flddph'
  COUTTAG  = '${CYR}'
  LOUTCDF  = .FALSE.   # ⚠️ BIN格式
  NDLEVEL  = 0
  IFRQ_OUT = 24
  /
  # ... (后面配置同NC格式) ...
EOFN

echo "Running CaMa-Flood BIN format..."
time ./MAIN_cmf

echo "Results saved in: ${RDIR}"
ls -lh ${RDIR}/*.bin
```

### 任务4: 完整运行流程（新流域）

**🤖 自动化检查（推荐）**:

在运行CaMa-Flood之前，使用自动检查脚本验证所有前置条件：

```bash
cd /Volumes/Expansion2t/hydro-model-workspace/skills/cama-flood-integration
./check_prerequisites.sh bengbu 2024
```

脚本会自动检查：
- VIC输出文件
- NetCDF径流数据
- CaMa地图文件（最容易出错）
- 河道参数
- 输入矩阵
- 1min高分辨率数据

如果检查通过，会显示 `✅ 全部检查通过！可以运行CaMa-Flood模拟`

---

**🔍 手动检查清单**（如果不使用自动脚本）:

#### VIC相关
- [ ] VIC模型已成功运行（无错误）
- [ ] VIC后处理已生成 `outputs/{basin}/cama_input/{basin}_runoff_1d_YYYY.nc`
- [ ] 验证NetCDF文件大小合理（>100KB）
- [ ] 检查变量名为'Runoff'且单位为'mm/day'

#### CaMa地图准备（🚨 最容易出错）
- [ ] **已创建新的地图目录** `map/{basin}_15min/`（不是manual_{basin}）
- [ ] **已完成步骤2.1（区域化）**: 检查 `nextxy.bin`, `ctmare.bin` 等文件存在
- [ ] **已完成步骤2.2（输入矩阵）**: 检查 `diminfo_{basin}_025deg.txt` 和 `inpmat_{basin}_025deg.bin` 存在
- [ ] **已完成步骤2.3（河道参数）**: 检查 `rivwth.bin`, `rivhgt.bin`, `rivman.bin` 存在
- [ ] **1min目录已生成**: 检查 `map/{basin}_15min/1min/` 存在（用于降尺度）

#### 运行脚本配置
- [ ] 运行脚本中使用**绝对路径**（避免相对路径错误）
- [ ] 所有地图文件路径指向 `map/{basin}_15min/`（不是manual_{basin}）
- [ ] 径流数据路径正确（绝对路径）

**步骤1: VIC后处理** (参见vic-auto-run skill)
```bash
cd scripts/vic_post
source /Users/yc/Desktop/project/python_env/bin/activate
python3 process_data_windows_ymd.py
```

**预期输出**:
- `outputs/{basin}/cama_input/runoff_YYYY.nc`

**步骤2: 地图准备三步骤** (⚠️ 每个新流域必须执行)

2.1 区域化:
```bash
cd model/cmf_v420_pkg/map/{basin}_15min/src_region
./s01-regional_map.sh
```

2.2 生成输入矩阵:
```bash
cd ../src_param
./s02-generate_inpmat.sh
```

2.3 生成河道参数:
```bash
./s01-channel_params.sh
```

**预期输出**:
- 地图文件: nextxy.bin, ctmare.bin, elevtn.bin, nxtdst.bin, rivlen.bin, fldhgt.bin
- 河道参数: rivwth_gwdlr.bin, rivhgt.bin, rivman.bin
- 映射文件: diminfo_{basin}_025deg.txt, inpmat_{basin}_025deg.bin
- 高分辨率: 1min/目录

**步骤3: 运行CaMa-Flood**

3.1 NC格式（完整变量）:
```bash
cd /Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/gosh
./run_{basin}_nc.sh
```

**预期输出** (in `outputs/{basin}/cama_nc/`):
- o_outflw{YYYY}.nc - 河道流量
- o_rivdph{YYYY}.nc - 河道水深
- o_sfcelv{YYYY}.nc - 水面高程
- o_flddph{YYYY}.nc - 洪泛区水深
- o_fldfrc{YYYY}.nc - 洪泛区面积比
- o_rivsto{YYYY}.nc - 河道蓄水量

3.2 BIN格式（用于降尺度）:
```bash
./run_{basin}_bin.sh
```

**预期输出** (in `outputs/{basin}/cama_bin/`):
- flddph{YYYY}.bin - 洪水淹没深度（BIN格式）

**🔴 降尺度准备**: 降尺度脚本期望bin文件在 `model/cmf_v420_pkg/out/{basin}_{YYYY}_bin/` 目录，需创建符号链接：
```bash
mkdir -p model/cmf_v420_pkg/out/{basin}_{YYYY}_bin
ln -sf /Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_bin/flddph{YYYY}.bin \
       model/cmf_v420_pkg/out/{basin}_{YYYY}_bin/flddph{YYYY}.bin
```

## 输出变量说明

### CaMa-Flood输出变量

| 变量 | 单位 | 描述 |
|------|------|------|
| outflw | m³/s | 河道出流流量 |
| rivdph | m | 河道水深 |
| sfcelv | m | 水面高程 (相对于海平面) |
| flddph | m | 洪泛区水深 |
| fldfrc | - | 洪泛区淹没面积比例 (0-1) |
| rivsto | m³ | 河道蓄水量 |
| fldsto | m³ | 洪泛区蓄水量 |
| fldare | m² | 洪泛区淹没面积 |

## 常见参数说明

### 模型参数

| 参数 | 符号 | 默认值 | 说明 |
|------|------|--------|------|
| 河道糙率 | PMANRIV | 0.03 | Manning系数 (河道) |
| 洪泛区糙率 | PMANFLD | 0.10 | Manning系数 (洪泛区) |
| 自适应时间步 | PCADP | 0.7 | CFL条件系数 |
| 扩散距离 | PDSTMTH | 10000 | 扩散方法距离阈值 (m) |

### 时间设置

- **DT**: 基础时间步长 (秒)
- **IFRQ_INP**: 输入数据频率 (小时)
- **IFRQ_OUT**: 输出数据频率 (小时)
- **IFRQ_RST**: 重启文件输出频率 (小时，0=关闭)

## 错误处理

### 问题1: STOP 10错误

**症状**: CaMa运行立即退出，显示`STOP 10`

**原因**: NetCDF文件读取错误，通常由以下原因引起：
1. 径流数据文件路径错误（使用了相对路径`../`）
2. 径流数据文件不存在
3. LINTERP插值配置错误

**解决**:
```bash
# 1. 检查径流文件是否存在
ls /Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_input/{basin}_runoff_1d_YYYY.nc

# 2. 使用绝对路径（不要用../）
CROFCDF = '/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_input/{basin}_runoff_1d_${CYR}.nc'

# 3. 使用LINTERP=.FALSE.（推荐）
LINTERP = .FALSE.
CINPMAT = ''

# 4. 查看详细日志
tail -50 log_CaMa.txt
```

### 问题2: 地图文件缺失

**症状**: `Error reading nextxy.bin` 或其他.bin文件错误

**原因**: 地图准备三步骤未完成或失败

**解决**:
```bash
# 检查地图文件是否存在
cd model/cmf_v420_pkg/map/{basin}_15min
ls -lh *.bin

# 应该包含以下文件:
# nextxy.bin, ctmare.bin, elevtn.bin, nxtdst.bin, rivlen.bin, fldhgt.bin
# rivwth_gwdlr.bin, rivhgt.bin, rivman.bin

# 如果缺失，重新运行地图准备三步骤
```

### 问题3: 径流气候态数据路径错误

**症状**: `calc_outclm`运行失败，找不到径流数据文件

**原因**: CROFBIN路径不正确

**解决**:
```bash
# 必须使用正确的绝对路径
CROFBIN="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map/data/ELSE_GPCC_coastmod_dayclm-1981-2010.one"

# 检查文件是否存在
ls -lh $CROFBIN
```

### 问题4: 高分辨率数据缺失（用于降尺度）

**症状**: `generate_inpmat`或降尺度时报错找不到1min/location.txt

**原因**: 区域化时未生成高分辨率数据

**解决**:
```bash
# 确保s01-regional_map.sh包含combine_hires步骤
# 检查1min目录是否存在
ls -lh model/cmf_v420_pkg/map/{basin}_15min/1min/

# 如果不存在，重新运行s01-regional_map.sh（完整版本）
```

### 问题5: 维度不匹配

**症状**: `Dimension mismatch` 或格网数量不对

**原因**: VIC网格与CaMa网格定义不一致

**解决**:
- 确认VIC后处理脚本中的NX, NY, WEST, EAST, NORTH, SOUTH
- 检查diminfo文件中的网格尺寸
- 确保generate_inpmat使用的边界与VIC一致

## 验证检查清单

运行前检查:
- [ ] VIC模型已成功运行，输出文件完整
- [ ] Python后处理脚本路径已配置
- [ ] CaMa-Flood可执行文件存在
- [ ] 区域化脚本已准备好

运行后验证:
- [ ] NetCDF输入文件已生成 (检查变量和维度)
- [ ] 地图文件已生成 (*.bin, diminfo, inpmat)
- [ ] CaMa-Flood运行无错误
- [ ] 输出NC文件已生成
- [ ] 流量数值合理 (outflw > 0)

## 使用示例

```bash
# 完整运行流程
cd /Volumes/Expansion2t/hydro-model-workspace

# 1. VIC后处理
source /Users/yc/Desktop/project/python_env/bin/activate
python3 scripts/vic_post/process_data_windows_ymd.py

# 2. CaMa-Flood区域化 (首次运行)
cd model/cmf_v420_pkg/map/bengbu_15min/src_region
./s01-regional_map.sh

# 3. 运行CaMa-Flood
cd ../../gosh
./run_bengbu_1d.sh

# 4. 查看结果
cd ../out/bengbu_2023
ls -lh *.nc
```

## 注意事项

1. **坐标系统**: 确保VIC和CaMa-Flood使用相同的坐标系统
2. **网格对齐**: 边界应与网格分辨率对齐 (0.25°的倍数)
3. **数据单位**: VIC输出单位为mm/day，需要转换
4. **时间一致性**: 确保VIC和CaMa-Flood的模拟时段一致
5. **内存需求**: 大流域可能需要较大内存
6. **Spin-up**: 首次运行建议进行1-2次spin-up以稳定初始条件

## 参考资料

- CaMa-Flood官方网站: http://hydro.iis.u-tokyo.ac.jp/~yamadai/cama-flood/
- CaMa-Flood GitHub: https://github.com/global-hydrodynamics/CaMa-Flood_v4
- 手册: `model/cmf_v420_pkg/doc/Manual_CaMa-Flood_v420.docx`
