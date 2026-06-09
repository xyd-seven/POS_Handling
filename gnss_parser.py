# -*- coding: utf-8 -*-
"""
GNSS 数据解析与精度计算引擎
"""
import math
import numpy as np
import functools
import operator
# WGS84 椭球体常数
WGS84_A = 6378137.0       # 长半轴
WGS84_B = 6356752.314245  # 短半轴
WGS84_E2 = 0.00669437999014  # 第一偏心率平方

def deg_to_nmea(deg, is_lat):
    """
    将浮点度数格式(dd.dddd)转换为 NMEA 的度分格式(ddmm.mmmmmmm)
    """
    abs_deg = abs(deg)
    d = int(abs_deg)
    m = (abs_deg - d) * 60
    
    d_str = str(d).zfill(2 if is_lat else 3)
    m_str = f"{m:.7f}"
    return f"{d_str}{m_str}"

def nmea_to_deg(raw, indicator, is_lat):
    """
    解析 NMEA 坐标字段 (ddmm.mmmm) 为十进制浮点度数 (dd.dddd)
    """
    if not raw or not indicator:
        return None
        
    dot_idx = raw.find('.')
    if dot_idx == -1:
        if len(raw) < 2: return None
        deg_str = raw[:-2]
        min_str = raw[-2:]
    else:
        if dot_idx < 2: return None
        deg_str = raw[:dot_idx-2]
        min_str = raw[dot_idx-2:]
    
    try:
        deg = int(deg_str) if deg_str else 0
        min_val = float(min_str)
    except ValueError:
        return None
        
    decimal = deg + (min_val / 60.0)
    if indicator in ['S', 'W']:
        decimal = -decimal
    return decimal

def calculate_checksum(sentence_body):
    """
    计算 NMEA 语句的 Checksum
    """
    checksum = functools.reduce(operator.xor, sentence_body.encode('ascii', errors='ignore'), 0)
    return f"{checksum:02X}"

def gps_tow_to_utc_time(tow, leap_seconds=18):
    """
    GPS周内秒 (TOW) 转换为 UTC 时间 (HHMMSS.ss)
    """
    utc_seconds = tow - leap_seconds
    if utc_seconds < 0:
        utc_seconds += 604800
        
    seconds_in_day = utc_seconds % 86400
    h = int(seconds_in_day // 3600)
    m = int((seconds_in_day % 3600) // 60)
    s = seconds_in_day % 60
    
    h_str = str(h).zfill(2)
    m_str = str(m).zfill(2)
    s_str = f"{s:.2f}".zfill(5)
    return f"{h_str}{m_str}{s_str}"

def lat_lon_to_enu(lat, lon, alt, lat0, lon0, alt0):
    """
    将经纬度高度转换为本地平面投影坐标（东北天 ENU 坐标系）
    支持标量和 Numpy 向量输入。
    """
    rad_lat = np.radians(lat)
    rad_lon = np.radians(lon)
    rad_lat0 = np.radians(lat0)
    rad_lon0 = np.radians(lon0)
    
    sin_lat0 = np.sin(rad_lat0)
    cos_lat0 = np.cos(rad_lat0)
    
    denom = 1.0 - WGS84_E2 * sin_lat0 * sin_lat0
    sqrt_denom = np.sqrt(denom)
    
    M = (WGS84_A * (1.0 - WGS84_E2)) / (denom * sqrt_denom)
    N = WGS84_A / sqrt_denom
    
    d_lat = rad_lat - rad_lat0
    d_lon = rad_lon - rad_lon0
    # 限制 d_lon 在 [-pi, pi] 之间以防止 180°/-180° 经度跨越产生的错误大跨度
    d_lon = (d_lon + np.pi) % (2 * np.pi) - np.pi
    
    dn = M * d_lat
    de = N * cos_lat0 * d_lon
    du = alt - alt0
    
    return de, dn, du

def format_time_str(raw):
    if not raw or len(raw) < 6:
        return raw
    h = raw[:2]
    m = raw[2:4]
    s = raw[4:]
    return f"{h}:{m}:{s}"

def time_str_to_seconds(raw):
    if not raw:
        return 0
    raw = raw.strip()
    if ':' in raw:
        parts = raw.split(':')
        try:
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2]) if len(parts) > 2 else 0.0
            return h * 3600 + m * 60 + s
        except (ValueError, IndexError):
            return 0
    else:
        if len(raw) < 6:
            return 0
        try:
            h = int(raw[:2])
            m = int(raw[2:4])
            s = float(raw[4:])
            return h * 3600 + m * 60 + s
        except ValueError:
            return 0

def seconds_to_time_str(secs):
    secs = max(0, secs % 86400)
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def parse_log_line(line, leap_seconds=18, strict_checksum=False):
    """
    解析单行 NMEA 或 POGOS 语句
    """
    line = line.strip()
    if not line.startswith('$'):
        return None
        
    star_idx = line.find('*')
    
    if strict_checksum and star_idx != -1 and len(line) >= star_idx + 3:
        expected = line[star_idx+1:star_idx+3].upper()
        actual = calculate_checksum(line[1:star_idx])
        if expected != actual:
            return None
            
    content = line[:star_idx] if star_idx != -1 else line
    parts = content.split(',')
    sentence_type = parts[0]
    
    # 1. GGA 语句
    if sentence_type.endswith('GGA'):
        if len(parts) < 10:
            return None
        utc_time = parts[1]
        try:
            lat_deg = nmea_to_deg(parts[2], parts[3], True)
            lon_deg = nmea_to_deg(parts[4], parts[5], False)
        except (ValueError, IndexError):
            return None
            
        try:
            quality = int(parts[6]) if parts[6].strip() else 0
            num_sats = int(parts[7]) if len(parts) > 7 and parts[7].strip() else 0
            hdop = float(parts[8]) if len(parts) > 8 and parts[8].strip() else 99.9
            alt = float(parts[9]) if len(parts) > 9 and parts[9].strip() else 0.0
            
            # 若存在大地水准面差距（Geoidal Separation，第 11 索引），则将其与海拔相加，换算为与 GOS/DRS 统一的 WGS84 椭球高 (HAE)
            if len(parts) > 11 and parts[11].strip():
                try:
                    alt += float(parts[11])
                except ValueError:
                    pass
        except ValueError:
            return None
            
        if lat_deg is None or lon_deg is None or lat_deg == 0.0 or lon_deg == 0.0:
            return None
            
        return {
            'type': 'GGA',
            'sentence_type': sentence_type,
            'time_str': format_time_str(utc_time),
            'utc_time_sec': time_str_to_seconds(utc_time),
            'lat': lat_deg,
            'lon': lon_deg,
            'alt': alt,
            'quality': quality,
            'num_sats': num_sats,
            'hdop': hdop,
            'raw_line': line
        }
        
    # 1.5 RMC 语句
    elif sentence_type.endswith('RMC'):
        if len(parts) < 10:
            return None
        utc_time = parts[1]
        status = parts[2]
        if status != 'A':
            return None
            
        try:
            lat_deg = nmea_to_deg(parts[3], parts[4], True)
            lon_deg = nmea_to_deg(parts[5], parts[6], False)
        except (ValueError, IndexError):
            return None
            
        quality = 1 # RMC 没有详细 RTK 状态，假设为单点有效
        alt = 0.0
        num_sats = 0
        hdop = 1.0
        
        if lat_deg is None or lon_deg is None or lat_deg == 0.0 or lon_deg == 0.0:
            return None
            
        return {
            'type': 'RMC',
            'sentence_type': sentence_type,
            'time_str': format_time_str(utc_time),
            'utc_time_sec': time_str_to_seconds(utc_time),
            'lat': lat_deg,
            'lon': lon_deg,
            'alt': alt,
            'quality': quality,
            'num_sats': num_sats,
            'hdop': hdop,
            'raw_line': line
        }

    # 2. 私有 POGOS (GOS) 语句
    elif sentence_type == '$POGOS':
        if len(parts) < 10:
            return None
        try:
            gps_week = int(parts[1])
            tow = float(parts[2])
            quality_raw = int(parts[6])
            lat = float(parts[7])
            lon = float(parts[8])
            alt = float(parts[9])
        except ValueError:
            return None
            
        if lat == 0.0 or lon == 0.0:
            return None
            
        utc_time_str = gps_tow_to_utc_time(tow, leap_seconds)
        
        quality = 0
        if quality_raw == 4:
            quality = 4  # RTK 固定
        elif quality_raw == 3:
            quality = 5  # RTK 浮点 (对应GGA的5)
        elif quality_raw == 2:
            quality = 2  # DGPS
        elif quality_raw == 1:
            quality = 1  # Single
        else:
            quality = quality_raw
            
        return {
            'type': 'POGOS',
            'sentence_type': '$POGOS',
            'time_str': format_time_str(utc_time_str),
            'utc_time_sec': time_str_to_seconds(utc_time_str),
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'quality': quality,
            'num_sats': 0,
            'hdop': 1.0,
            'raw_line': line
        }

    # 3. 私有 PODRS (DRS) 语句
    elif sentence_type == '$PODRS':
        if len(parts) < 8:
            return None
        try:
            gps_week = int(parts[1])
            tow = float(parts[2])
            quality_raw = int(parts[4])
            lat = float(parts[5])
            lon = float(parts[6])
            alt = float(parts[7])
        except ValueError:
            return None
            
        if lat == 0.0 or lon == 0.0:
            return None
            
        utc_time_str = gps_tow_to_utc_time(tow, leap_seconds)
        
        quality = 0
        if quality_raw == 4:
            quality = 4  # RTK 固定
        elif quality_raw == 3:
            quality = 5  # RTK 浮点 (对应GGA的5)
        elif quality_raw == 2:
            quality = 2  # DGPS
        elif quality_raw == 1:
            quality = 1  # Single
        else:
            quality = quality_raw
            
        return {
            'type': 'PODRS',
            'sentence_type': '$PODRS',
            'time_str': format_time_str(utc_time_str),
            'utc_time_sec': time_str_to_seconds(utc_time_str),
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'quality': quality,
            'num_sats': 0,
            'hdop': 1.0,
            'raw_line': line
        }
        
    # 4. GSA 语句
    elif sentence_type.endswith('GSA'):
        if len(parts) >= 18:
            try:
                pdop = float(parts[15]) if parts[15].strip() else 99.9
                hdop = float(parts[16]) if parts[16].strip() else 99.9
                vdop = float(parts[17]) if parts[17].strip() else 99.9
                return {
                    'type': 'GSA',
                    'sentence_type': sentence_type,
                    'pdop': pdop,
                    'hdop': hdop,
                    'vdop': vdop,
                    'raw_line': line
                }
            except ValueError:
                pass

    return {
        'type': 'OTHER',
        'sentence_type': sentence_type,
        'raw_line': line
    }

def convert_pogos_to_gga(line, talker_id='GN', leap_seconds=18):
    """
    将 POGOS 转换成 GGA
    """
    epoch = parse_log_line(line, leap_seconds)
    if not epoch or epoch['type'] != 'POGOS':
        return None
        
    lat_nmea = deg_to_nmea(epoch['lat'], True)
    lat_dir = 'N' if epoch['lat'] >= 0 else 'S'
    
    lon_nmea = deg_to_nmea(epoch['lon'], False)
    lon_dir = 'E' if epoch['lon'] >= 0 else 'W'
    
    time_clean = epoch['time_str'].replace(':', '')
    
    body = f"{talker_id}GGA,{time_clean},{lat_nmea},{lat_dir},{lon_nmea},{lon_dir},{epoch['quality']},{epoch['num_sats']:02d},{epoch['hdop']:.1f},{epoch['alt']:.3f},M,-0.0,M,,"
    checksum = calculate_checksum(body)
    return f"${body}*{checksum}"

def unwrap_times(times):
    if len(times) == 0:
        return np.array(times, dtype=float)
    times_arr = np.array(times, dtype=float)
    diffs = np.diff(times_arr)
    wraps = np.zeros(len(diffs))
    wraps[diffs < -43200.0] = 86400.0
    wraps[diffs > 43200.0] = -86400.0
    times_arr[1:] += np.cumsum(wraps)
    return times_arr

def interpolate_dynamic_truth(test_epochs, truth_epochs, max_time_diff=1.0):
    """
    针对待测轨迹中的时间戳，在真值轨迹中进行线性插值。
    返回插值后一一对应的动态真值序列。超时的返回 None。
    """
    if not test_epochs or not truth_epochs:
        return None
        
    truth_times = unwrap_times([ep['utc_time_sec'] for ep in truth_epochs])
    truth_lats = np.array([ep['lat'] for ep in truth_epochs])
    truth_lons = np.array([ep['lon'] for ep in truth_epochs])
    truth_alts = np.array([ep['alt'] for ep in truth_epochs])
    
    test_times = unwrap_times([ep['utc_time_sec'] for ep in test_epochs])
    
    # 保证 test_times 和 truth_times 的平均时间在一个数量级，避免跨午夜文件未合并产生的绝对日期偏移
    if len(truth_times) > 0 and len(test_times) > 0:
        mean_truth = np.mean(truth_times)
        mean_test = np.mean(test_times)
        diff_days = round((mean_truth - mean_test) / 86400.0)
        test_times += diff_days * 86400.0
        
    # 确保真值序列时间单调递增，去重排序
    sort_idx = np.argsort(truth_times)
    truth_times = truth_times[sort_idx]
    truth_lats = truth_lats[sort_idx]
    truth_lons = truth_lons[sort_idx]
    truth_alts = truth_alts[sort_idx]
    
    # 简单的剔除完全重复时间戳
    diffs = np.diff(truth_times)
    unique_mask = np.insert(diffs != 0, 0, True)
    truth_times = truth_times[unique_mask]
    truth_lats = truth_lats[unique_mask]
    truth_lons = truth_lons[unique_mask]
    truth_alts = truth_alts[unique_mask]
    
    if len(truth_times) < 2:
        return None
    
    # 插值
    interp_lats = np.interp(test_times, truth_times, truth_lats, left=np.nan, right=np.nan)
    interp_lons = np.interp(test_times, truth_times, truth_lons, left=np.nan, right=np.nan)
    interp_alts = np.interp(test_times, truth_times, truth_alts, left=np.nan, right=np.nan)
    
    # 寻找最近点来判断是否超时
    # np.searchsorted
    idx = np.searchsorted(truth_times, test_times)
    idx = np.clip(idx, 1, len(truth_times) - 1)
    
    left_diff = np.abs(test_times - truth_times[idx - 1])
    right_diff = np.abs(test_times - truth_times[idx])
    min_diff = np.minimum(left_diff, right_diff)
    
    valid_mask = (min_diff <= max_time_diff) & (~np.isnan(interp_lats))
    
    dynamic_truth = []
    for i in range(len(test_epochs)):
        if valid_mask[i]:
            dynamic_truth.append({
                'lat': interp_lats[i],
                'lon': interp_lons[i],
                'alt': interp_alts[i]
            })
        else:
            dynamic_truth.append(None)
            
    return dynamic_truth

def calculate_metrics(points, truth, filter_outliers=False, outlier_thresh=1000.0, dynamic_truth_array=None):
    """
    计算定位点集相对于真值的精度指标 (向量化加速版)
    支持静态真值 (truth 字典) 和动态真值 (dynamic_truth_array)
    """
    if not points:
        return None, points
        
    original_count = len(points)
    
    if dynamic_truth_array is not None:
        # 过滤掉 dynamic_truth 为 None 的点
        valid_indices = [i for i, t in enumerate(dynamic_truth_array) if t is not None]
        points = [points[i] for i in valid_indices]
        dynamic_truth_array = [dynamic_truth_array[i] for i in valid_indices]
        
    n_total = len(points)
    if n_total == 0:
        return {
            'count': 0,
            'original_count': original_count,
            'rtk_fix_count': 0,
            'rtk_fix_rate': 0.0,
            'enu_points': [],
            'h_errors': [],
            'v_errors': [],
            'cep50': 0.0,
            'cep68': 0.0,
            'cep95': 0.0,
            'rms_h': 0.0,
            'rms_v': 0.0,
            'max_h': 0.0,
            'max_v': 0.0,
            'de': [],
            'dn': []
        }, points
        
    # 提取数组进行批量运算
    lats = np.array([p['lat'] for p in points])
    lons = np.array([p['lon'] for p in points])
    alts = np.array([p['alt'] for p in points])
    qualities = np.array([p['quality'] for p in points])
    
    if dynamic_truth_array is not None:
        t_lats = np.array([t['lat'] for t in dynamic_truth_array])
        t_lons = np.array([t['lon'] for t in dynamic_truth_array])
        t_alts = np.array([t['alt'] for t in dynamic_truth_array])
        de, dn, du = lat_lon_to_enu(lats, lons, alts, t_lats, t_lons, t_alts)
    else:
        de, dn, du = lat_lon_to_enu(lats, lons, alts, truth['lat'], truth['lon'], truth['alt'])
    
    h_err = np.sqrt(de*de + dn*dn)
    
    if filter_outliers:
        valid_mask = h_err <= outlier_thresh
        if not np.all(valid_mask):
            valid_indices = np.where(valid_mask)[0]
            points = [points[i] for i in valid_indices]
            de = de[valid_mask]
            dn = dn[valid_mask]
            du = du[valid_mask]
            h_err = h_err[valid_mask]
            qualities = qualities[valid_mask]
            n_total = len(points)
            if n_total == 0:
                return None, points
                
    sum_e2 = np.sum(de*de)
    sum_n2 = np.sum(dn*dn)
    sum_u2 = np.sum(du*du)
    
    max_h_dev = float(np.max(h_err))
    max_v_dev = float(np.max(np.abs(du)))
    
    rtk_fix_count = np.sum(qualities == 4)
    
    # 兼容之前结构
    enu_points = [{'e': float(e), 'n': float(n), 'u': float(u)} for e, n, u in zip(de, dn, du)]
    
    # 使用 NumPy 官方的百分位数插值算法计算，比简单的索引取值更科学精确
    cep50 = float(np.percentile(h_err, 50.0)) if n_total > 0 else 0.0
    cep68 = float(np.percentile(h_err, 68.0)) if n_total > 0 else 0.0
    cep95 = float(np.percentile(h_err, 95.0)) if n_total > 0 else 0.0
    
    rms_h = float(np.sqrt((sum_e2 + sum_n2) / n_total)) if n_total > 0 else 0.0
    rms_v = float(np.sqrt(sum_u2 / n_total)) if n_total > 0 else 0.0
    
    metrics = {
        'count': n_total,
        'original_count': original_count,
        'rtk_fix_count': int(rtk_fix_count),
        'rtk_fix_rate': float((rtk_fix_count / n_total) * 100.0) if n_total > 0 else 0.0,
        'cep50': cep50,
        'cep68': cep68,
        'cep95': cep95,
        'rms_h': rms_h,
        'rms_v': rms_v,
        'max_h': max_h_dev,
        'max_v': max_v_dev,
        'enu_points': enu_points,
        'h_errors': h_err.tolist() if isinstance(h_err, np.ndarray) else h_err,
        'v_errors': du.tolist() if isinstance(du, np.ndarray) else du,
        'de': de.tolist() if isinstance(de, np.ndarray) else de,
        'dn': dn.tolist() if isinstance(dn, np.ndarray) else dn
    }
    return metrics, points
