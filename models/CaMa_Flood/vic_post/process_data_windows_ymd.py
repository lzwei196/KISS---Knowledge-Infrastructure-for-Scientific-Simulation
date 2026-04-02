# -*- coding: utf-8 -*-
import os
import glob
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm

# ==============================================================================
# 1. 用户配置区 (请根据您的新要求配置好)
# ==============================================================================
# 输入1d VIC结果的路径
INPUT_DIR = "/Volumes/Expansion4t/hydro-space/outputs/bengbu_vic_routing_2023_2024/vic_result"

# 输出NetCDF文件的路径
OUTPUT_DIR = "/Volumes/Expansion4t/hydro-space/outputs/bengbu_vic_routing_2023_2024/cama_input"

# VIC文件名格式 (vic文件名是 huaihe_fluxes_lat_lon.txt)
FILE_PREFIX = "huaihe_fluxes_"
FILE_SUFFIX = ".txt"

# 【关键】【修改】请在这里定义您想提取的精确日期范围
START_DATE = "2023-01-01"  # 起始日期，格式 'YYYY-MM-DD'
END_DATE = "2024-12-31"    # 结束日期，格式 'YYYY-MM-DD'

# NetCDF中数据变量的名称
VAR_NAME = "Runoff"
VAR_UNITS = "mm/day"

# NetCDF文件名前缀
OUTPUT_NC_PREFIX = "bengbu_runoff_1d_"

# 地图的精确定义 (王家坝流域 - 匹配CaMa地图维度)
NX = 24        # 地图的东西方向格点数 (匹配CaMa: 24)
NY = 16        # 地图的南北方向格点数 (匹配CaMa: 16)
WEST = 111.75  # 地图西边界 (°)
EAST = 117.75  # 地图东边界 (°)
NORTH = 35.0   # 地图北边界 (°)
SOUTH = 31.0   # 地图南边界 (°)
GRID_SIZE = 0.25 # 地图格网分辨率 (°)
# ==============================================================================
# 2. 脚本主程序
# ==============================================================================
def main():
    """主函数，读取日尺度VIC数据，筛选指定日期范围，计算总径流，并按年份生成NetCDF文件"""
    print("脚本开始执行...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 步骤 1: 根据地图元数据精确重建坐标轴 ---
    print("步骤 1: 精确重建CaMa-Flood坐标系...")
    cama_lons = np.linspace(WEST + GRID_SIZE / 2, EAST - GRID_SIZE / 2, NX)
    cama_lats = np.linspace(NORTH - GRID_SIZE / 2, SOUTH + GRID_SIZE / 2, NY)
    print("CaMa-Flood坐标系重建成功。")

    # --- 步骤 2: 扫描VIC数据文件 ---
    search_path = os.path.join(INPUT_DIR, f"{FILE_PREFIX}*.txt")
    file_list = glob.glob(search_path)
    if not file_list:
        print(f"错误: 在目录 {INPUT_DIR} 中未找到任何匹配的VIC数据文件。")
        return
    print(f"找到 {len(file_list)} 个VIC数据文件。")

    # --- 步骤 3: 读取所有VIC数据并映射到CaMa-Flood网格 ---
    print(f"目标时间范围: {START_DATE} 到 {END_DATE}")
    time_coords = pd.date_range(start=START_DATE, end=END_DATE, freq='D')
    total_days_in_range = len(time_coords)
    print(f"共计 {total_days_in_range} 天。")

    all_data = np.full((total_days_in_range, NY, NX), -9999.0, dtype=np.float32)

    lon_map = {val: i for i, val in enumerate(cama_lons)}
    lat_map = {val: i for i, val in enumerate(cama_lats)}

    for f_path in tqdm(file_list, desc="正在读取并映射VIC文件"):
        try:
            filename = os.path.basename(f_path)
            parts = filename.replace(FILE_PREFIX, "").replace(FILE_SUFFIX, "").split('_')
            lat, lon = float(parts[0]), float(parts[1])

            # 找到最接近的CaMa-Flood格点
            closest_lon = min(cama_lons, key=lambda x:abs(x-lon))
            closest_lat = min(cama_lats, key=lambda x:abs(x-lat))

            if closest_lon in lon_map and closest_lat in lat_map:
                ix = lon_map[closest_lon]
                iy = lat_map[closest_lat]

                # 读取整个文件
                df = pd.read_csv(f_path, sep=r'\s+', comment='#', header=0)

                # 创建日期索引
                df['dates'] = pd.to_datetime(df[['YEAR', 'MONTH', 'DAY']])
                df.set_index('dates', inplace=True)

                # 根据精确的日期范围来筛选数据
                df_filtered = df.loc[START_DATE:END_DATE]

                # 计算总径流
                point_data = (df_filtered['OUT_RUNOFF'] + df_filtered['OUT_BASEFLOW']).to_numpy(dtype=np.float32)

                # 检查筛选后的天数是否与目标天数一致
                if point_data.shape[0] == total_days_in_range:
                    all_data[:, iy, ix] = point_data

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")

    # --- 步骤 4: 按年份写入NetCDF文件 ---
    print("步骤 4: 按年份生成NetCDF文件...")

    # 解析起止年份
    start_year = pd.to_datetime(START_DATE).year
    end_year = pd.to_datetime(END_DATE).year

    current_idx = 0
    nc_files = []

    for year in range(start_year, end_year + 1):
        # 创建该年的时间坐标
        year_time_coords = pd.date_range(
            start=f'{year}-01-01',
            end=f'{year}-12-31',
            freq='D'
        )
        num_days = len(year_time_coords)

        # 检查是否还有足够的数据
        if current_idx >= total_days_in_range:
            print(f"警告: 年份{year}数据不足，跳过")
            break

        # 计算实际可用的天数
        available_days = min(num_days, total_days_in_range - current_idx)

        # 提取该年的数据
        year_data = all_data[current_idx:current_idx + available_days, :, :]

        # 创建DataArray with standard calendar
        runoff_da = xr.DataArray(
            data=year_data,
            coords={
                "time": year_time_coords[:available_days],
                "lat": cama_lats,
                "lon": cama_lons,
            },
            dims=["time", "lat", "lon"],
            name=VAR_NAME,
        )

        # 设置属性
        runoff_da.attrs['units'] = VAR_UNITS
        runoff_da.attrs['long_name'] = f'Total Runoff (Surface Runoff + Baseflow) for {year}'
        runoff_da.attrs['description'] = 'VIC masked grid mapped to CAMA full grid'
        runoff_da.lat.attrs['units'] = 'degrees_north'
        runoff_da.lat.attrs['long_name'] = 'Latitude'
        runoff_da.lon.attrs['units'] = 'degrees_east'
        runoff_da.lon.attrs['long_name'] = 'Longitude'

        # 写入NetCDF with standard calendar
        output_filename = os.path.join(OUTPUT_DIR, f"{OUTPUT_NC_PREFIX}{year}.nc")

        # Create dataset to add global attributes
        ds = runoff_da.to_dataset()
        ds.attrs['title'] = 'CAMA-Flood runoff forcing'
        ds.attrs['source'] = 'VIC masked output mapped to CAMA grid'
        ds.attrs['cama_grid'] = f'{NX}x{NY}'
        ds.attrs['cama_extent'] = f'{WEST}E-{EAST}E, {SOUTH}N-{NORTH}N'
        ds.attrs['conversion_date'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        ds.to_netcdf(
            output_filename,
            encoding={
                VAR_NAME: {
                    "_FillValue": -9999.0,
                    "dtype": "float32",
                    "zlib": True,
                    "complevel": 4
                },
                "time": {
                    "units": f"days since {year}-01-01 00:00:00",
                    "calendar": "standard"
                }
            }
        )

        nc_files.append(output_filename)
        current_idx += available_days
        print(f"  生成: {output_filename}")

    print(f"\n任务完成！生成了 {len(nc_files)} 个NetCDF文件")

if __name__ == '__main__':
    main()
