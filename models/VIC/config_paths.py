#!/usr/bin/env python3
"""
VIC模型路径配置脚本
自动修改所有Python脚本中的路径为当前工作空间路径
"""

import os
from pathlib import Path
import re

# 工作空间根目录
WORKSPACE_ROOT = Path("/mnt/disk1/Hydrocraft_server")

# 流域名称配置（用于输出目录）
BASIN_NAME = "xixian_rerun_71379b42"

# 路径配置字典
PATH_CONFIG = {
    # 数据路径
    "shp_dir": WORKSPACE_ROOT / "data" / "shp" / "xixian_025deg_shp" / "xixian_boundary_shp",
    "shp_file": WORKSPACE_ROOT / "data" / "shp" / "xixian_025deg_shp" / "xixian_boundary_shp" / "xixian_boundary.shp",
    "forcing_nc_dir": WORKSPACE_ROOT / "data" / "forcing" / "Data_forcing_03hr_010deg",
    "soil_raster": WORKSPACE_ROOT / "data" / "soil" / "HWSD_China_Geo.img",
    "landcover_raster": WORKSPACE_ROOT / "data" / "landcover" / "AVHRR_1km_LANDCOVER_1981_1994.GLOBAL.tif",
    "global_soil_param": WORKSPACE_ROOT / "data" / "插值" / "global_soil_param_new.txt",
    "elev_nc": WORKSPACE_ROOT / "data" / "elev" / "elev_CMFD_V0200_B-00_fx_010deg.nc",
    "his_average_prec_nc": WORKSPACE_ROOT / "data" / "his_average_prec" / "prec_CMFD_010deg_meanAnnual_1951-2020_mm.nc",
    "his_average_prec": WORKSPACE_ROOT / "data" / "his_average_prec",

    # 输出路径 (使用流域专属目录)
    "output_grid_nc": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "grid" / f"grid_{BASIN_NAME}_025deg.nc",
    "output_forcing_1d": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "forcing" / "forcing_1d",
    "output_forcing_final": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "forcing" / "forcing_final",
    "output_soil_dir": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "soil",
    "output_soil_param_1": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "soil" / "SOIL_PARAM_FINAL.txt",
    "output_soil_param_2": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "soil" / "SOIL_PARAM_COMPLETE.txt",
    "output_veg_param": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "veg" / "vic_veg_param_final.txt",
    "output_vic_result": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_result",

    # 参数文件
    "veglib_file": WORKSPACE_ROOT / "data" / "vic_param" / "veglib.LDAS",
    "global_param_template": WORKSPACE_ROOT / "outputs" / "xixian_1979-1990_test" / "vic_temp" / "global_param_xixian_1979-1990_test.txt",
    "global_param_output": WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / f"global_param_{BASIN_NAME}.txt",

    # VIC可执行文件
    "vic_exe": WORKSPACE_ROOT / "model" / "VIC-5.1.0" / "vic" / "drivers" / "classic" / "vic_classic.exe",
}

# 脚本路径映射
SCRIPTS_CONFIG = {
    "s1_grid/make_basin_grid_nc.py": {
        "BASIN_SHP": "shp_file",
        "OUT_GRID_NC": "output_grid_nc",
    },
    "s2_forcing/forcing_1d.py": {
        "INPUT_DATA_DIR": "forcing_nc_dir",
        "OUTPUT_DIR": "output_forcing_1d",
    },
    "s2_forcing/process_forcing.py": {
        "INPUT_DATA_DIR": "output_forcing_1d",  # 使用forcing_1d的输出
        "OUTPUT_FORCING_DIR": "output_forcing_final",
        "SOIL_PARAM_FILE": "output_soil_param_2",
    },
    "s3_soil/fill_parameters1.py": {
        "MASTER_GRID_NC": "output_grid_nc",
        "ELEV_NC_IN": "elev_nc",
        "PREC_ANNUAL_NC": "his_average_prec_nc",
        "SOIL_RASTER_IN": "soil_raster",
        "OUTPUT_DIR": "output_soil_dir",
    },
    "s3_soil/fill_parameters2.py": {
        "SOIL_PARAM_IN": "output_soil_param_1",
        "GLOBAL_SOIL_FILE": "global_soil_param",
        "SOIL_PARAM_OUT": "output_soil_param_2",
    },
    "s4_veg/process_vegetation_detailed.py": {
        "MASTER_GRID_NC": "output_grid_nc",
        "VEG_RASTER_IN": "landcover_raster",
        "VEGLIB_FILE": "veglib_file",
        "VEG_PARAM_OUT": "output_veg_param",
    },
}


def create_output_dirs():
    """创建所有必需的输出目录"""
    dirs_to_create = [
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "grid",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "forcing" / "forcing_1d",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "forcing" / "forcing_final",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "soil",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "veg",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_temp" / "logs",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "vic_result",
        WORKSPACE_ROOT / "outputs" / BASIN_NAME / "cama_input",
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")


SCRIPTS_DIR = WORKSPACE_ROOT / "skills" / "vic-auto-run"


def update_script_paths(script_rel_path, var_mapping):
    """更新单个脚本中的路径变量"""
    script_path = SCRIPTS_DIR / script_rel_path

    if not script_path.exists():
        print(f"✗ 脚本不存在: {script_path}")
        return False

    # 读取脚本内容
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 备份原始文件
    backup_path = script_path.with_suffix('.py.bak')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 替换路径
    modified = False
    for var_name, config_key in var_mapping.items():
        new_path = PATH_CONFIG[config_key]

        # 特殊处理OUTPUT_DIR（fill_parameters1.py中OUTPUT_DIR不是Path类型）
        if var_name == "OUTPUT_DIR" and "fill_parameters1" in script_rel_path:
            # 匹配模式: OUTPUT_DIR = Path(r"...")
            pattern = rf'{var_name}\s*=\s*Path\(r?"[^"]*"\)'
            replacement = f'{var_name} = Path(r"{new_path}")'
        else:
            # 匹配模式: VAR_NAME = Path(r"...")
            pattern = rf'{var_name}\s*=\s*Path\(r?"[^"]*"\)'
            replacement = f'{var_name} = Path(r"{new_path}")'

        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
            print(f"  ✓ 更新 {var_name} = {new_path}")
        else:
            print(f"  ⚠️  未找到变量 {var_name}")

    # 写回文件
    if modified:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ 已更新脚本: {script_rel_path}")
        return True
    else:
        print(f"⚠️  脚本未修改: {script_rel_path}")
        return False


def create_global_param():
    """创建配置好路径的全局参数文件"""
    template_path = PATH_CONFIG["global_param_template"]
    output_path = PATH_CONFIG["global_param_output"]

    if not template_path.exists():
        print(f"✗ 模板文件不存在: {template_path}")
        return False

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换关键路径
    replacements = {
        r'FORCING1\s+.*': f'FORCING1                {PATH_CONFIG["output_forcing_final"]}/huai_01dy_025deg_',
        r'SOIL\s+.*': f'SOIL                    {PATH_CONFIG["output_soil_param_2"]}',
        r'VEGLIB\s+.*': f'VEGLIB                  {PATH_CONFIG["veglib_file"]}',
        r'VEGPARAM\s+.*': f'VEGPARAM                {PATH_CONFIG["output_veg_param"]}',
        r'RESULT_DIR\s+.*': f'RESULT_DIR              {PATH_CONFIG["output_vic_result"]}/',
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ 已创建全局参数文件: {output_path}")
    return True


def check_required_files():
    """检查必需的输入文件是否存在"""
    print("\n" + "="*80)
    print("检查必需文件")
    print("="*80)

    required_files = [
        ("流域边界", PATH_CONFIG["shp_file"]),
        ("全球土壤参数", PATH_CONFIG["global_soil_param"]),
        ("地表覆盖栅格", PATH_CONFIG["landcover_raster"]),
        ("植被库文件", PATH_CONFIG["veglib_file"]),
        ("VIC可执行文件", PATH_CONFIG["vic_exe"]),
    ]

    all_exist = True
    for name, path in required_files:
        if path.exists():
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name} 不存在: {path}")
            all_exist = False

    # 检查气象数据目录
    forcing_dir = PATH_CONFIG["forcing_nc_dir"]
    if forcing_dir.exists():
        nc_files = list(forcing_dir.rglob("*.nc"))
        print(f"✓ 气象数据目录: {forcing_dir} (包含 {len(nc_files)} 个NC文件)")
    else:
        print(f"✗ 气象数据目录不存在: {forcing_dir}")
        all_exist = False

    return all_exist


def main():
    """主函数"""
    print("="*80)
    print("VIC模型路径配置脚本")
    print("="*80)
    print(f"工作空间: {WORKSPACE_ROOT}")
    print(f"流域名称: {BASIN_NAME}")
    print("="*80)

    # 1. 检查必需文件
    if not check_required_files():
        print("\n⚠️  警告：部分必需文件不存在，请检查后再继续")
        response = input("是否继续配置路径？(y/n): ")
        if response.lower() != 'y':
            return

    # 2. 创建输出目录
    print("\n" + "="*80)
    print("创建输出目录")
    print("="*80)
    create_output_dirs()

    # 3. 更新脚本路径
    print("\n" + "="*80)
    print("更新脚本路径")
    print("="*80)

    for script_path, var_mapping in SCRIPTS_CONFIG.items():
        print(f"\n处理脚本: {script_path}")
        update_script_paths(script_path, var_mapping)

    # 4. 创建全局参数文件
    print("\n" + "="*80)
    print("创建全局参数文件")
    print("="*80)
    create_global_param()

    # 5. 输出配置总结
    print("\n" + "="*80)
    print("配置完成！")
    print("="*80)
    print("\n下一步操作：")
    print("1. 检查各脚本的路径配置是否正确")
    print("2. 依次运行以下命令：")
    print(f"   cd {WORKSPACE_ROOT}/scripts/s1_grid && python make_basin_grid_nc.py")
    print(f"   cd {WORKSPACE_ROOT}/scripts/s2_forcing && python forcing_1d.py")
    print(f"   cd {WORKSPACE_ROOT}/scripts/s2_forcing && python process_forcing.py")
    print(f"   cd {WORKSPACE_ROOT}/scripts/s3_soil && python fill_parameters1.py")
    print(f"   cd {WORKSPACE_ROOT}/scripts/s3_soil && python fill_parameters2.py")
    print(f"   cd {WORKSPACE_ROOT}/scripts/s4_veg && python process_vegetation_detailed.py")
    print(f"3. 运行VIC模型：")
    print(f"   {PATH_CONFIG['vic_exe']} -g {PATH_CONFIG['global_param_output']}")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
