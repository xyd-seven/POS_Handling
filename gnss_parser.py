# -*- coding: utf-8 -*-
"""
GNSS 数据解析与精度计算引擎
"""
import math
import numpy as np
import functools
import operator
import struct
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
    
    def _clean_str(s):
        if not s:
            return ""
        # 移除非法控制字符，保留基本数字、点、负号和字母
        return ''.join(c for c in s.strip() if c.isalnum() or c in '.-+')

    def _extract_float(s, default=None):
        if not s:
            return default
        import re
        m = re.search(r'[-+]?\d*\.?\d+', s)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return default
        return default

    def _extract_int(s, default=0):
        if not s:
            return default
        import re
        m = re.search(r'\d+', s)
        if m:
            try:
                return int(m.group(0))
            except ValueError:
                return default
        return default

    # 1. GGA 语句
    if sentence_type.endswith('GGA'):
        if len(parts) < 10:
            return None
        utc_time = parts[1]
        
        raw_lat = parts[2].strip()
        raw_lat_hemi = parts[3].strip().upper()
        raw_lon = parts[4].strip()
        raw_lon_hemi = parts[5].strip().upper()
        
        # 半球自愈提取（若出现 E?4 或 E4 粘连）
        lat_hemi = raw_lat_hemi[0] if raw_lat_hemi and raw_lat_hemi[0] in ['N', 'S'] else raw_lat_hemi
        lon_hemi = raw_lon_hemi[0] if raw_lon_hemi and raw_lon_hemi[0] in ['E', 'W'] else raw_lon_hemi
        
        quality_str = parts[6].strip() if len(parts) > 6 else ""
        # 若 raw_lon_hemi 包含后续数字（如 'E?4' 或 'E4'），且 quality_str 无效，回填 quality
        if len(raw_lon_hemi) > 1 and not quality_str.isdigit():
            digits = ''.join([c for c in raw_lon_hemi[1:] if c.isdigit()])
            if digits:
                quality_str = digits[0]

        try:
            lat_deg = nmea_to_deg(raw_lat, lat_hemi, True)
            lon_deg = nmea_to_deg(raw_lon, lon_hemi, False)
        except (ValueError, IndexError):
            return None
            
        try:
            quality = _extract_int(quality_str, 1)
            num_sats = _extract_int(parts[7], 0) if len(parts) > 7 else 0
            hdop = _extract_float(parts[8], 99.9) if len(parts) > 8 else 99.9
            alt = _extract_float(parts[9], None) if len(parts) > 9 else None
            
            # 若存在大地水准面差距（Geoidal Separation，第 11 索引），则将其与海拔相加，换算为 WGS84 椭球高 (HAE)
            if alt is not None and len(parts) > 11 and parts[11].strip():
                geoid_sep = _extract_float(parts[11], 0.0)
                if geoid_sep is not None:
                    alt += geoid_sep
        except Exception:
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
        alt = None # RMC 规范无高程字段，显式置为 None
        num_sats = 0
        hdop = 1.0
        
        # 提取速度: RMC 第7字段为节 (Knots), 1 knot = 0.5144444 m/s
        ground_speed = 0.0
        if len(parts) > 7 and parts[7].strip():
            sp_val = _extract_float(parts[7], 0.0)
            if sp_val is not None:
                ground_speed = sp_val * 0.5144444
        
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
            'ground_speed': ground_speed,
            'quality': quality,
            'num_sats': num_sats,
            'hdop': hdop,
            'raw_line': line
        }

    # 1.8 GSV 语句 (可见卫星信息)
    elif sentence_type.endswith('GSV'):
        if len(parts) < 4:
            return None
        try:
            total_msg = int(parts[1])
            msg_num = int(parts[2])
            total_sats = int(parts[3])
        except ValueError:
            return None
            
        # 识别星座前缀
        prefix = 'GPS'
        if 'BD' in sentence_type or 'GB' in sentence_type:
            prefix = 'BD'
        elif 'GL' in sentence_type:
            prefix = 'GL'
        elif 'GA' in sentence_type:
            prefix = 'GA'
        elif 'IR' in sentence_type or 'GI' in sentence_type:
            prefix = 'IRNSS'
            
        sats = []
        signal_id = '1' # 默认频段 ID
        sat_fields_len = len(parts) - 4
        if sat_fields_len > 0 and sat_fields_len % 4 == 1:
            signal_id = parts[-1].strip()
            loop_parts = parts[:-1]
        else:
            loop_parts = parts
            
        idx = 4
        while idx + 3 < len(loop_parts):
            prn_str = loop_parts[idx].strip()
            elev_str = loop_parts[idx+1].strip()
            azim_str = loop_parts[idx+2].strip()
            snr_str = loop_parts[idx+3].strip()
            if prn_str:
                try:
                    prn = int(prn_str)
                    elev = int(elev_str) if elev_str else None
                    azim = int(azim_str) if azim_str else None
                    snr = int(snr_str) if snr_str else 0
                    sats.append({
                        'prn': prn,
                        'elevation': elev,
                        'azimuth': azim,
                        'snr': snr
                    })
                except ValueError:
                    pass
            idx += 4
            
        return {
            'type': 'GSV',
            'sentence_type': sentence_type,
            'prefix': prefix,
            'total_msg': total_msg,
            'msg_num': msg_num,
            'total_sats': total_sats,
            'signal_id': signal_id,
            'sats': sats,
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
                sats_used = []
                for p in parts[3:15]:
                    p = p.strip()
                    if p:
                        try:
                            sats_used.append(int(p))
                        except ValueError:
                            pass
                return {
                    'type': 'GSA',
                    'sentence_type': sentence_type,
                    'pdop': pdop,
                    'hdop': hdop,
                    'vdop': vdop,
                    'sats_used': sats_used,
                    'raw_line': line
                }
            except ValueError:
                pass

    # 4.5. POSOL 语句
    elif sentence_type == '$POSOL':
        if len(parts) < 27:
            return None
        utc_time = parts[1]
        date_str = parts[2]
        try:
            lat_deg = nmea_to_deg(parts[3], parts[4], True)
            lon_deg = nmea_to_deg(parts[5], parts[6], False)
        except (ValueError, IndexError):
            return None
            
        try:
            orth = float(parts[7]) if parts[7].strip() else 0.0
            geoid = float(parts[8]) if parts[8].strip() else 0.0
            alt = orth + geoid
            
            std_lat = float(parts[9]) if parts[9].strip() else 0.0
            std_lon = float(parts[10]) if parts[10].strip() else 0.0
            std_alt = float(parts[11]) if parts[11].strip() else 0.0
            
            vel_e = float(parts[13]) if parts[13].strip() else 0.0
            vel_n = float(parts[14]) if parts[14].strip() else 0.0
            vel_u = float(parts[15]) if parts[15].strip() else 0.0
            
            course = float(parts[19]) if parts[19].strip() else 0.0
            num_sats = int(parts[21]) if parts[21].strip() else 0
            num_usv = int(parts[22]) if parts[22].strip() else 0
            
            pdop = float(parts[23]) if parts[23].strip() else 99.9
            hdop = float(parts[24]) if parts[24].strip() else 99.9
            vdop = float(parts[25]) if parts[25].strip() else 99.9
            
            quality = int(parts[26]) if parts[26].strip() else 0
            
            age = float(parts[27]) if len(parts) > 27 and parts[27].strip() else 0.0
        except ValueError:
            return None
            
        if lat_deg is None or lon_deg is None or lat_deg == 0.0 or lon_deg == 0.0:
            return None
            
        ground_speed = (vel_e**2 + vel_n**2)**0.5

        return {
            'type': 'POSOL',
            'sentence_type': '$POSOL',
            'time_str': format_time_str(utc_time),
            'utc_time_sec': time_str_to_seconds(utc_time),
            'date': date_str,
            'lat': lat_deg,
            'lon': lon_deg,
            'alt': alt,
            'orth': orth,
            'geoid': geoid,
            'std_lat': std_lat,
            'std_lon': std_lon,
            'std_alt': std_alt,
            'vel_e': vel_e,
            'vel_n': vel_n,
            'vel_u': vel_u,
            'ground_speed': ground_speed,
            'course': course,
            'quality': quality,
            'num_sats': num_sats,
            'num_usv': num_usv,
            'pdop': pdop,
            'hdop': hdop,
            'vdop': vdop,
            'age': age,
            'raw_line': line
        }

    # 4.6. POINS 语句
    elif sentence_type == '$POINS':
        if len(parts) < 28:
            return None
        try:
            gps_week = int(parts[1]) if parts[1].strip() else 0
            gps_seconds = float(parts[2]) if parts[2].strip() else 0.0
            ins_status = int(parts[3]) if parts[3].strip() else 0
            imu_status = int(parts[4]) if parts[4].strip() else 0
            gnss_status = int(parts[5]) if parts[5].strip() else 0
            odometer_status = int(parts[6]) if parts[6].strip() else 0
            motion_status = int(parts[7]) if parts[7].strip() else 0
            imu_type = int(parts[8]) if parts[8].strip() else 0
            work_mode = int(parts[9]) if parts[9].strip() else 0
            
            roll = float(parts[10]) if parts[10].strip() else 0.0
            pitch = float(parts[11]) if parts[11].strip() else 0.0
            yaw = float(parts[12]) if parts[12].strip() else 0.0
            
            speed_status = int(parts[13]) if parts[13].strip() else 0
            lane_status = int(parts[14]) if parts[14].strip() else 0
            lean_status = int(parts[15]) if parts[15].strip() else 0
            bump_status = int(parts[16]) if parts[16].strip() else 0
            
            velocity_forward = float(parts[17]) if parts[17].strip() else 0.0
            velocity_rightward = float(parts[18]) if parts[18].strip() else 0.0
            velocity_downward = float(parts[19]) if parts[19].strip() else 0.0
            
            drive_mileage = float(parts[20]) if parts[20].strip() else 0.0
            work_time = float(parts[21]) if parts[21].strip() else 0.0
            
            acceler_forward = float(parts[22]) if parts[22].strip() else 0.0
            acceler_rightward = float(parts[23]) if parts[23].strip() else 0.0
            acceler_downward = float(parts[24]) if parts[24].strip() else 0.0
            
            angular_roll = float(parts[25]) if parts[25].strip() else 0.0
            angular_pitch = float(parts[26]) if parts[26].strip() else 0.0
            angular_yaw = float(parts[27]) if parts[27].strip() else 0.0
        except ValueError:
            return None
            
        return {
            'type': 'POINS',
            'sentence_type': '$POINS',
            'gps_week': gps_week,
            'gps_tow': gps_seconds,
            'ins_status': ins_status,
            'imu_status': imu_status,
            'gnss_status': gnss_status,
            'odometer_status': odometer_status,
            'motion_status': motion_status,
            'imu_type': imu_type,
            'work_mode': work_mode,
            'roll': roll,
            'pitch': pitch,
            'yaw': yaw,
            'speed_status': speed_status,
            'lane_status': lane_status,
            'lean_status': lean_status,
            'bump_status': bump_status,
            'velocity_forward': velocity_forward,
            'velocity_rightward': velocity_rightward,
            'velocity_downward': velocity_downward,
            'drive_mileage': drive_mileage,
            'work_time': work_time,
            'acceler_forward': acceler_forward,
            'acceler_rightward': acceler_rightward,
            'acceler_downward': acceler_downward,
            'angular_roll': angular_roll,
            'angular_pitch': angular_pitch,
            'angular_yaw': angular_yaw,
            'raw_line': line
        }

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

def attach_rmc_speed_to_epochs(file_epochs):
    """
    智能跨语句融合：提取数据流中 RMC/POSOL/POINS 的高精度原生测速 (ground_speed)，
    自动按时间对齐融合挂载到同秒的 GGA 历元字典中 (ep['ground_speed'] = ...)。
    """
    if not file_epochs:
        return file_epochs
        
    speed_events = []
    for ep in file_epochs:
        sp = ep.get('ground_speed')
        if sp is not None and isinstance(sp, (int, float)):
            speed_events.append((ep['utc_time_sec'], float(sp)))
        elif ep.get('type') == 'POSOL' and 'vel_e' in ep and 'vel_n' in ep:
            speed_events.append((ep['utc_time_sec'], float((ep['vel_e']**2 + ep['vel_n']**2)**0.5)))
        elif ep.get('type') == 'POINS' and 'velocity_forward' in ep and 'velocity_rightward' in ep:
            speed_events.append((ep['utc_time_sec'], float((ep['velocity_forward']**2 + ep['velocity_rightward']**2)**0.5)))
            
    if not speed_events:
        return file_epochs
        
    speed_events.sort(key=lambda x: x[0])
    sp_times = np.array([item[0] for item in speed_events])
    sp_vals = np.array([item[1] for item in speed_events])
    
    # 遍历 GGA 或未带速度的历元，进行最近邻/插值挂载
    for ep in file_epochs:
        if ep.get('ground_speed') is None:
            t = ep.get('utc_time_sec')
            if t is not None:
                idx = np.searchsorted(sp_times, t)
                idx = np.clip(idx, 0, len(sp_times) - 1)
                best_sp = None
                best_dt = 999.0
                for c_idx in (idx - 1, idx, idx + 1):
                    if 0 <= c_idx < len(sp_times):
                        dt = abs(sp_times[c_idx] - t)
                        if dt <= 1.0 and dt < best_dt:
                            best_dt = dt
                            best_sp = sp_vals[c_idx]
                if best_sp is not None:
                    ep['ground_speed'] = float(best_sp)
                    
    return file_epochs

def extract_or_compute_speed(epochs):
    """
    安全提取历元序列的地面速度 (m/s)。
    1. 优先提取每个历元中的原生速度 ground_speed (来自 RMC/POSOL/POINS/BK)；
    2. 若部分历元有原生速度 (>50%)，对个别缺失历元进行时间线性插补；
    3. 仅当完全没有原生速度时，利用相邻经纬度距离微分推导。
    """
    if not epochs:
        return np.array([])
        
    n = len(epochs)
    speeds = []
    valid_times = []
    valid_speeds = []
    times = unwrap_times([ep.get('utc_time_sec', 0.0) for ep in epochs])
    
    for i, ep in enumerate(epochs):
        if not isinstance(ep, dict):
            break
        sp = ep.get('ground_speed')
        if sp is not None and isinstance(sp, (int, float)):
            valid_times.append(times[i])
            valid_speeds.append(float(sp))
            speeds.append(float(sp))
        elif ep.get('type') == 'POSOL' and 'vel_e' in ep and 'vel_n' in ep:
            val = float((ep['vel_e']**2 + ep['vel_n']**2)**0.5)
            valid_times.append(times[i])
            valid_speeds.append(val)
            speeds.append(val)
        elif ep.get('type') == 'POINS' and 'velocity_forward' in ep and 'velocity_rightward' in ep:
            val = float((ep['velocity_forward']**2 + ep['velocity_rightward']**2)**0.5)
            valid_times.append(times[i])
            valid_speeds.append(val)
            speeds.append(val)
        else:
            speeds.append(np.nan)
            
    # 若大部分或全部点拥有原生速度，进行缺失点平滑插补后返回
    if len(valid_speeds) > 0 and len(valid_speeds) >= n * 0.5:
        if len(valid_speeds) == n and not np.any(np.isnan(speeds)):
            return np.array(speeds, dtype=float)
            
        valid_times = np.array(valid_times)
        valid_speeds = np.array(valid_speeds)
        sort_idx = np.argsort(valid_times)
        valid_times = valid_times[sort_idx]
        valid_speeds = valid_speeds[sort_idx]
        
        diffs = np.diff(valid_times)
        umask = np.insert(diffs != 0, 0, True)
        valid_times = valid_times[umask]
        valid_speeds = valid_speeds[umask]
        
        if len(valid_times) == 1:
            clean_speeds = np.full(n, valid_speeds[0], dtype=float)
        else:
            clean_speeds = np.interp(times, valid_times, valid_speeds, left=valid_speeds[0], right=valid_speeds[-1])
        return clean_speeds
        
    # 微分推导速度
    speeds_arr = np.zeros(n, dtype=float)
    if n < 2:
        return speeds_arr
        
    lats = np.array([ep['lat'] for ep in epochs])
    lons = np.array([ep['lon'] for ep in epochs])
    
    # 转换为局域 ENU 计算相邻两点欧式距离
    de, dn, _ = lat_lon_to_enu(lats[1:], lons[1:], 0, lats[:-1], lons[:-1], 0)
    dist = np.sqrt(de**2 + dn**2)
    dt = np.diff(times)
    
    dt_safe = np.where((dt > 0.001) & (dt < 10.0), dt, 1.0)
    inst_speed = np.where((dt > 0.001) & (dt < 10.0), dist / dt_safe, 0.0)
    
    speeds_arr[0] = float(inst_speed[0]) if len(inst_speed) > 0 else 0.0
    speeds_arr[1:] = inst_speed
    return speeds_arr

def clean_and_interpolate_altitudes(epochs):
    """
    通用高程提纯与平滑插补函数（适用于待测数据与真值数据）。
    1. 剔除 None、NaN 及绝对值 <= 1e-4 的伪 0 高程；
    2. 基于有效测高点沿时间轴进行 1D 线性平滑插补；
    3. 彻底防止 0 高程引发的深坑或伪尖峰。
    """
    if not epochs:
        return np.array([])
        
    n = len(epochs)
    raw_alts = []
    valid_times = []
    valid_alts = []
    
    times = unwrap_times([ep.get('utc_time_sec', 0.0) for ep in epochs])
    
    for i, ep in enumerate(epochs):
        a = ep.get('alt')
        if a is not None and isinstance(a, (int, float)) and not np.isnan(a) and abs(a) > 1e-4 and ep.get('type') != 'RMC':
            valid_times.append(times[i])
            valid_alts.append(float(a))
            raw_alts.append(float(a))
        else:
            raw_alts.append(np.nan)
            
    if not valid_alts:
        return np.zeros(n, dtype=float)
        
    if len(valid_alts) == n and not np.any(np.isnan(raw_alts)):
        return np.array(raw_alts, dtype=float)
        
    # 对缺失高程的历元进行时间线性插补
    valid_times = np.array(valid_times)
    valid_alts = np.array(valid_alts)
    
    # 保证单调递增
    sort_idx = np.argsort(valid_times)
    valid_times = valid_times[sort_idx]
    valid_alts = valid_alts[sort_idx]
    
    # 去重
    diffs = np.diff(valid_times)
    umask = np.insert(diffs != 0, 0, True)
    valid_times = valid_times[umask]
    valid_alts = valid_alts[umask]
    
    if len(valid_times) == 1:
        clean_alts = np.full(n, valid_alts[0], dtype=float)
    else:
        clean_alts = np.interp(times, valid_times, valid_alts, left=valid_alts[0], right=valid_alts[-1])
        
    # 回填到 epochs
    for i, ep in enumerate(epochs):
        ep['alt'] = float(clean_alts[i])
        
    return clean_alts

def interpolate_dynamic_truth(test_epochs, truth_epochs, max_time_diff=1.0):
    """
    针对待测轨迹中的时间戳，在真值轨迹中进行线性插值。
    经纬度、高程、速度分别独立提纯插值。超时的返回 None。
    """
    if not test_epochs or not truth_epochs:
        return None
        
    truth_times = unwrap_times([ep['utc_time_sec'] for ep in truth_epochs])
    truth_lats = np.array([ep['lat'] for ep in truth_epochs])
    truth_lons = np.array([ep['lon'] for ep in truth_epochs])
    truth_alts = clean_and_interpolate_altitudes(truth_epochs)
    truth_speeds = extract_or_compute_speed(truth_epochs)
    
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
    if len(truth_speeds) == len(truth_epochs):
        truth_speeds = truth_speeds[sort_idx]
    
    # 简单的剔除完全重复时间戳
    diffs = np.diff(truth_times)
    unique_mask = np.insert(diffs != 0, 0, True)
    truth_times = truth_times[unique_mask]
    truth_lats = truth_lats[unique_mask]
    truth_lons = truth_lons[unique_mask]
    truth_alts = truth_alts[unique_mask]
    if len(truth_speeds) == len(truth_times):
        truth_speeds = truth_speeds[unique_mask]
    
    if len(truth_times) < 2:
        return None
    
    # 插值
    interp_lats = np.interp(test_times, truth_times, truth_lats, left=np.nan, right=np.nan)
    interp_lons = np.interp(test_times, truth_times, truth_lons, left=np.nan, right=np.nan)
    interp_alts = np.interp(test_times, truth_times, truth_alts, left=np.nan, right=np.nan)
    if len(truth_speeds) == len(truth_times):
        interp_speeds = np.interp(test_times, truth_times, truth_speeds, left=np.nan, right=np.nan)
    else:
        interp_speeds = np.zeros(len(test_times), dtype=float)
    
    # 寻找最近点来判断是否超时
    idx = np.searchsorted(truth_times, test_times)
    idx = np.clip(idx, 1, len(truth_times) - 1)
    
    left_diff = np.abs(test_times - truth_times[idx - 1])
    right_diff = np.abs(test_times - truth_times[idx])
    min_diff = np.minimum(left_diff, right_diff)
    
    valid_mask = (min_diff <= max_time_diff) & (~np.isnan(interp_lats)) & (~np.isnan(interp_alts))
    
    dynamic_truth = []
    for i in range(len(test_epochs)):
        if valid_mask[i]:
            dynamic_truth.append({
                'lat': float(interp_lats[i]),
                'lon': float(interp_lons[i]),
                'alt': float(interp_alts[i]),
                'speed': float(interp_speeds[i]) if not np.isnan(interp_speeds[i]) else 0.0
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
            'dn': [],
            'speed_test': [],
            'speed_truth': [],
            'speed_errors': [],
            'speed_ave': 0.0,
            'speed_std': 0.0,
            'speed_rms': 0.0,
            'speed_max': 0.0
        }, points
        
    # 待测点集高程提纯与平滑插补
    alts = clean_and_interpolate_altitudes(points)
    lats = np.array([p['lat'] for p in points])
    lons = np.array([p['lon'] for p in points])
    qualities = np.array([p.get('quality', 1) for p in points])
    
    # 提取速度
    speed_test = extract_or_compute_speed(points)
    
    if dynamic_truth_array is not None:
        t_lats = np.array([t['lat'] for t in dynamic_truth_array])
        t_lons = np.array([t['lon'] for t in dynamic_truth_array])
        t_alts = np.array([t['alt'] for t in dynamic_truth_array])
        speed_truth = np.array([t.get('speed', 0.0) for t in dynamic_truth_array])
        de, dn, du = lat_lon_to_enu(lats, lons, alts, t_lats, t_lons, t_alts)
    else:
        de, dn, du = lat_lon_to_enu(lats, lons, alts, truth['lat'], truth['lon'], truth['alt'])
        speed_truth = np.zeros(n_total, dtype=float)
    
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
            speed_test = speed_test[valid_mask]
            speed_truth = speed_truth[valid_mask]
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
    
    # 计算速度误差统计
    speed_errors = speed_test - speed_truth
    speed_ave = float(np.mean(speed_errors)) if n_total > 0 else 0.0
    speed_std = float(np.std(speed_errors)) if n_total > 0 else 0.0
    speed_rms = float(np.sqrt(np.mean(speed_errors**2))) if n_total > 0 else 0.0
    speed_max = float(np.max(np.abs(speed_errors))) if n_total > 0 else 0.0
    
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
        'dn': dn.tolist() if isinstance(dn, np.ndarray) else dn,
        'speed_test': speed_test.tolist() if isinstance(speed_test, np.ndarray) else speed_test,
        'speed_truth': speed_truth.tolist() if isinstance(speed_truth, np.ndarray) else speed_truth,
        'speed_errors': speed_errors.tolist() if isinstance(speed_errors, np.ndarray) else speed_errors,
        'speed_ave': speed_ave,
        'speed_std': speed_std,
        'speed_rms': speed_rms,
        'speed_max': speed_max
    }
    return metrics, points

def _init_crc16_table():
    table = []
    for i in range(256):
        crc = 0
        c = i << 8
        for _ in range(8):
            if (crc ^ c) & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            c <<= 1
            crc &= 0xFFFF
        table.append(crc)
    return table

CRC16_CCITT_TABLE = _init_crc16_table()

def crc16_ccitt(data: bytes) -> int:
    """
    计算 CCITT CRC-16 校验值 (多项式 0x1021, 初始值 0x0000) - 查表加速版
    """
    crc = 0
    for b in data:
        crc = (crc << 8) ^ CRC16_CCITT_TABLE[((crc >> 8) ^ b) & 0xFF]
        crc &= 0xFFFF
    return crc

def parse_bk_frame(frame: bytes) -> dict:
    """
    解析完整的 BK 协议二进制帧
    """
    if len(frame) < 8:
        return None
    if frame[0] != 0x42 or frame[1] != 0x4B:
        return None
        
    crc_pkg = (frame[2] << 8) | frame[3]
    mtype = frame[4]
    stype = frame[5]
    len_msb = frame[6]
    len_lsb = frame[7]
    
    payload_len = ((len_msb & 0x0F) << 8) | len_lsb
    if len(frame) != 8 + payload_len:
        return None
        
    # 计算 MTYPE 到 Payload 结束的 CRC
    crc_calc = crc16_ccitt(frame[4:])
    if crc_calc != crc_pkg:
        return None
        
    payload = frame[8:]
    
    # 解析 BK_PNT_NAV (MTYPE=0x41, STYPE=0x00, 长度60字节)
    if mtype == 0x41 and stype == 0x00:
        if len(payload) != 60:
            return None
            
        try:
            fields = struct.unpack("<H6BBBBBH8B8B9e3i", payload)
        except Exception:
            return None
            
        ms = fields[0]
        sec = fields[1]
        minute = fields[2]
        hour = fields[3]
        day = fields[4]
        month = fields[5]
        year = fields[6]
        flags = fields[7]
        num_sats = fields[8]
        pdop = fields[9] * 0.1
        version = fields[10]
        gnss_system_bitmap = fields[11]
        
        cno_vals = fields[12:20]
        sv_num_vals = fields[20:28]
        
        h_acc = fields[28]
        v_acc = fields[29]
        s_acc = fields[30]
        heading_acc = fields[31]
        vel_n = fields[32]
        vel_e = fields[33]
        vel_d = fields[34]
        ground_speed = fields[35]
        heading = fields[36]
        
        lon_raw = fields[37]
        lat_raw = fields[38]
        alt_raw = fields[39]
        
        # 换算: 经度纬度按 10^-7 换算，高度按 10^-3 换算
        lon_deg = lon_raw * 1e-7
        lat_deg = lat_raw * 1e-7
        alt = alt_raw / 1000.0  # mm -> m
        
        quality = flags & 0x07  # bit0-2
        
        # 格式化 UTC 时间字符串 hhmmss.ss
        time_str = f"{hour:02d}{minute:02d}{sec:02d}.{ms//10:02d}"
        utc_time_sec = hour * 3600 + minute * 60 + sec + (ms / 1000.0)
        
        return {
            'type': 'BK_PNT_NAV',
            'sentence_type': '$BK_PNT_NAV',
            'time_str': format_time_str(time_str),
            'utc_time_sec': utc_time_sec,
            'lat': lat_deg,
            'lon': lon_deg,
            'alt': alt,
            'quality': quality,
            'num_sats': num_sats,
            'hdop': pdop,  # 用 pdop 代替 hdop 展示
            'pdop': pdop,
            'h_acc': h_acc,
            'v_acc': v_acc,
            's_acc': s_acc,
            'heading_acc': heading_acc,
            'vel_n': vel_n,
            'vel_e': vel_e,
            'vel_d': vel_d,
            'ground_speed': ground_speed,
            'heading': heading,
            'raw_line': frame.hex()
        }
        
    return {
        'type': 'OTHER_BK',
        'mtype': mtype,
        'stype': stype,
        'payload': payload.hex()
    }

def check_nmea_header(buffer: bytearray, start_idx: int) -> bool:
    """
    检查缓冲区中 start_idx 开始的字符是否像是一个合法的 NMEA 语句开头。
    合法特征：$ 后面跟着 2 到 10 个字母或数字组成的 talker/sentence 标识符，并紧邻 ,、*、\r 或 \n 结束。
    """
    if len(buffer) < start_idx + 4:
        return True
    idx = start_idx + 1
    length = len(buffer)
    header_len = 0
    
    first_char = buffer[idx]
    if not ((65 <= first_char <= 90) or (97 <= first_char <= 122)):
        return False
        
    while idx < length:
        char = buffer[idx]
        if char == 44 or char == 42 or char == 13 or char == 10:  # ',' 或 '*' 或 '\r' 或 '\n'
            return 2 <= header_len <= 10
        is_alphanumeric = (65 <= char <= 90) or (97 <= char <= 122) or (48 <= char <= 57)
        if not is_alphanumeric:
            return False
        header_len += 1
        idx += 1
        if header_len > 10:
            return False
    return True

class BKStreamParser:
    """
    流式协议分包器，从输入流中切分出 NMEA 明文行与 BK 二进制协议帧
    """
    def __init__(self):
        self.buffer = bytearray()
        
    def feed(self, data: bytes):
        self.buffer.extend(data)
        
    def next_frame(self):
        """
        尝试从缓冲区中提取下一个完整的帧/行
        返回: (frame_type, frame_data) 或 None
        """
        while len(self.buffer) > 0:
            # 查找第一个特征字节：$ 或 0x42
            idx_nmea = self.buffer.find(b'$')
            idx_bk = self.buffer.find(b'\x42')
            
            # 确定谁在前
            first_idx = -1
            mode = None
            if idx_nmea != -1 and idx_bk != -1:
                if idx_nmea < idx_bk:
                    first_idx = idx_nmea
                    mode = 'NMEA'
                else:
                    first_idx = idx_bk
                    mode = 'BK'
            elif idx_nmea != -1:
                first_idx = idx_nmea
                mode = 'NMEA'
            elif idx_bk != -1:
                first_idx = idx_bk
                mode = 'BK'
                
            if first_idx == -1:
                # 没有任何同步字，清空
                self.buffer.clear()
                return None
                
            # 抛弃同步字前面的垃圾字节
            if first_idx > 0:
                del self.buffer[:first_idx]
                
            # 执行分包
            if mode == 'NMEA':
                # 在分包前，先校验 NMEA 句头是否合法以防假同步
                if not check_nmea_header(self.buffer, 0):
                    del self.buffer[:1]
                    continue
                    
                # 寻找换行符 \n
                idx_nl = self.buffer.find(b'\n')
                if idx_nl == -1:
                    return None
                line_data = self.buffer[:idx_nl + 1]
                del self.buffer[:idx_nl + 1]
                return 'NMEA', line_data
                
            elif mode == 'BK':
                if len(self.buffer) < 2:
                    return None
                # 检查下一个字节是否为 0x4B
                if self.buffer[1] != 0x4B:
                    # 假同步，抛弃 0x42
                    del self.buffer[:1]
                    continue
                    
                if len(self.buffer) < 8:
                    return None
                    
                len_msb = self.buffer[6]
                len_lsb = self.buffer[7]
                payload_len = ((len_msb & 0x0F) << 8) | len_lsb
                total_len = 8 + payload_len
                
                if len(self.buffer) < total_len:
                    return None
                    
                frame_data = self.buffer[:total_len]
                del self.buffer[:total_len]
                return 'BK', frame_data
                
        return None
