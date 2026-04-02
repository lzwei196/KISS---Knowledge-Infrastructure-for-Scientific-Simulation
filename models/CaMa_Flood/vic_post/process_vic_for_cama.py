#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VIC输出转CaMa-Flood输入格式
将VIC的格点文本文件转换为CaMa需要的NetCDF格式
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
from datetime import datetime
import argparse

def find_runoff_columns(header_line):
    """根据表头找到RUNOFF和BASEFLOW的列索引"""
    cols = header_line.strip().split()
    runoff_idx = None
    baseflow_idx = None
    for i, col in enumerate(cols):
        if 'OUT_RUNOFF' in col:
            runoff_idx = i
        elif 'OUT_BASEFLOW' in col:
            baseflow_idx = i
    return runoff_idx, baseflow_idx

def process_vic_output(input_dir, output_dir, start_year, end_year,
                       file_prefix="huaihe_fluxes_", output_prefix="bengbu"):
    """
    处理VIC输出文件并生成CaMa输入NetCDF文件
    """
    os.makedirs(output_dir, exist_ok=True)

    # 获取所有VIC输出文件
    pattern = os.path.join(input_dir, f"{file_prefix}*.txt")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"错误: 在 {input_dir} 中未找到匹配 {file_prefix}*.txt 的文件")
        return False

    print(f"找到 {len(files)} 个VIC输出文件")

    # 读取第一个文件确定列索引和时间范围
    sample_file = files[0]
    with open(sample_file, 'r') as f:
        lines = f.readlines()

    # 跳过注释行，找到表头
    header_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('YEAR'):
            header_idx = i
            break

    header = lines[header_idx]
    runoff_idx, baseflow_idx = find_runoff_columns(header)

    if runoff_idx is None or baseflow_idx is None:
        print(f"错误: 无法在表头中找到RUNOFF或BASEFLOW列")
        print(f"表头: {header}")
        return False

    print(f"RUNOFF列索引: {runoff_idx}, BASEFLOW列索引: {baseflow_idx}")

    # 提取坐标信息
    coords = []
    for f in files:
        basename = os.path.basename(f)
        # 从文件名提取坐标: huaihe_fluxes_33.1250_117.1250.txt
        parts = basename.replace(file_prefix, '').replace('.txt', '').split('_')
        if len(parts) >= 2:
            lat = float(parts[0])
            lon = float(parts[1])
            coords.append((lat, lon, f))

    # 确定网格范围
    lats = sorted(set([c[0] for c in coords]), reverse=True)  # 北到南
    lons = sorted(set([c[1] for c in coords]))  # 西到东

    print(f"纬度范围: {min(lats):.4f} - {max(lats):.4f}, 共 {len(lats)} 个")
    print(f"经度范围: {min(lons):.4f} - {max(lons):.4f}, 共 {len(lons)} 个")

    # 按年处理
    for year in range(start_year, end_year + 1):
        print(f"\n处理 {year} 年...")

        # 确定该年的天数
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            ndays = 366
        else:
            ndays = 365

        # 创建数据数组 (time, lat, lon)
        runoff_data = np.full((ndays, len(lats), len(lons)), np.nan, dtype=np.float32)

        # 读取每个格点的数据
        for lat, lon, filepath in coords:
            lat_idx = lats.index(lat)
            lon_idx = lons.index(lon)

            try:
                # 读取数据，跳过表头
                df = pd.read_csv(filepath, sep=r'\s+', skiprows=header_idx+1, header=None)

                # 筛选当年数据
                df_year = df[df.iloc[:, 0] == year].copy()

                if len(df_year) == 0:
                    continue

                # 提取径流数据 (RUNOFF + BASEFLOW)
                runoff = df_year.iloc[:, runoff_idx].values + df_year.iloc[:, baseflow_idx].values

                # 填入数组
                runoff_data[:len(runoff), lat_idx, lon_idx] = runoff

            except Exception as e:
                print(f"  警告: 处理 {filepath} 时出错: {e}")
                continue

        # 保存为NetCDF
        try:
            import netCDF4 as nc

            output_file = os.path.join(output_dir, f"{output_prefix}_runoff_1d_{year}.nc")

            with nc.Dataset(output_file, 'w', format='NETCDF4') as ds:
                # 创建维度
                ds.createDimension('time', ndays)
                ds.createDimension('lat', len(lats))
                ds.createDimension('lon', len(lons))

                # 创建时间变量
                time_var = ds.createVariable('time', 'i4', ('time',))
                time_var.units = f'days since {year}-01-01'
                time_var.calendar = 'standard'
                time_var[:] = np.arange(ndays)

                # 创建坐标变量
                lat_var = ds.createVariable('lat', 'f4', ('lat',))
                lat_var.units = 'degrees_north'
                lat_var[:] = lats

                lon_var = ds.createVariable('lon', 'f4', ('lon',))
                lon_var.units = 'degrees_east'
                lon_var[:] = lons

                # 创建径流变量
                runoff_var = ds.createVariable('Runoff', 'f4', ('time', 'lat', 'lon'),
                                               fill_value=-9999.0)
                runoff_var.units = 'mm/day'
                runoff_var.long_name = 'Total Runoff (surface + baseflow)'
                runoff_var[:] = runoff_data

                # 全局属性
                ds.title = f'VIC Runoff for CaMa-Flood ({year})'
                ds.source = 'VIC 5.1.0'
                ds.history = f'Created {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

            print(f"  保存: {output_file}")

        except ImportError:
            print("错误: 需要安装netCDF4库")
            return False

    print(f"\n处理完成! 输出目录: {output_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(description='VIC输出转CaMa-Flood输入格式')
    parser.add_argument('--input', required=True, help='VIC输出目录')
    parser.add_argument('--output', required=True, help='CaMa输入目录')
    parser.add_argument('--start', type=int, required=True, help='起始年份')
    parser.add_argument('--end', type=int, required=True, help='结束年份')
    parser.add_argument('--prefix', default='huaihe_fluxes_', help='VIC文件前缀')
    parser.add_argument('--outprefix', default='bengbu', help='输出文件前缀')

    args = parser.parse_args()

    success = process_vic_output(
        input_dir=args.input,
        output_dir=args.output,
        start_year=args.start,
        end_year=args.end,
        file_prefix=args.prefix,
        output_prefix=args.outprefix
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
