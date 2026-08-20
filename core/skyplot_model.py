# -*- coding: utf-8 -*-
"""
雷达极坐标天空图数据模型与时序索引提取器
支持 O(1) 秒级快速切片检索、星轨轨迹提取及多源 GSV/GSA 状态合并。
"""
import bisect
import numpy as np
from gnss_parser import get_sat_info

class SkyPlotDataModel:
    def __init__(self):
        self.time_list = []
        self.time_to_sats = {}  # time_sec -> {sat_key: sat_dict}
        self.time_to_dop = {}   # time_sec -> {'pdop': float, 'hdop': float, 'vdop': float, 'num_sats': int}
        self.all_sat_tracks = {} # sat_key -> list of (time_sec, elevation, azimuth, is_used)

    def clear(self):
        self.time_list.clear()
        self.time_to_sats.clear()
        self.time_to_dop.clear()
        self.all_sat_tracks.clear()

    def build_from_epochs(self, epochs):
        """
        从解析得到的历元列表构建天空图时序索引
        """
        self.clear()
        if not epochs:
            return

        # 遍历解析 GSV/GSA/GGA/BK 历元
        current_sats = {}
        for ep in epochs:
            t = ep.get('utc_time_sec')
            if t is None:
                continue

            ep_type = ep.get('type', '')
            
            if ep_type == 'GSV':
                prefix = ep.get('prefix', '')
                msg_num = ep.get('msg_num', 1)
                
                # 若是第 1 帧 GSV，清空对应系统的旧卫星缓存
                if msg_num == 1:
                    keys_to_del = [k for k in current_sats if k[0] == prefix]
                    for k in keys_to_del:
                        del current_sats[k]

                for s in ep.get('sats', []):
                    prn = s.get('prn')
                    elev = s.get('elevation')
                    azim = s.get('azimuth')
                    snr = s.get('snr', 0)
                    if prn is None or elev is None or azim is None:
                        continue
                    if not (0 <= elev <= 90 and 0 <= azim <= 360):
                        continue

                    sys_prefix, real_prn, lbl_char = get_sat_info(prefix, prn)
                    sat_key = (sys_prefix, real_prn)
                    current_sats[sat_key] = {
                        'sys_prefix': sys_prefix,
                        'prn': real_prn,
                        'lbl_char': lbl_char,
                        'elevation': float(elev),
                        'azimuth': float(azim),
                        'snr': float(snr),
                        'is_used': False
                    }

            elif ep_type in ['GGA', 'POSOL', 'BK_PNT_NAV', 'POGOS', 'PODRS']:
                # 保存当前秒切片
                sats_copy = {k: dict(v) for k, v in current_sats.items()}
                
                # 记录 DOP
                dop_info = {
                    'pdop': float(ep.get('pdop', 1.0) if ep.get('pdop') is not None else 1.0),
                    'hdop': float(ep.get('hdop', 1.0) if ep.get('hdop') is not None else 1.0),
                    'vdop': float(ep.get('vdop', 1.0) if ep.get('vdop') is not None else 1.0),
                    'num_sats': int(ep.get('num_sats', len(sats_copy))),
                    'quality': int(ep.get('quality', 0))
                }

                if t not in self.time_to_sats:
                    self.time_list.append(t)
                    self.time_to_sats[t] = sats_copy
                    self.time_to_dop[t] = dop_info
                else:
                    self.time_to_sats[t].update(sats_copy)
                    self.time_to_dop[t] = dop_info

                # 更新全时段星轨
                for k, v in sats_copy.items():
                    if k not in self.all_sat_tracks:
                        self.all_sat_tracks[k] = []
                    self.all_sat_tracks[k].append((t, v['elevation'], v['azimuth'], v['is_used']))

        self.time_list.sort()

    def get_snapshot_at_time(self, time_sec):
        """
        以 O(1) 速度二分定位获取指定时间戳的天空图快照与 DOP
        """
        if not self.time_list:
            return {}, {'pdop': 1.0, 'hdop': 1.0, 'vdop': 1.0, 'num_sats': 0, 'quality': 0}

        idx = bisect.bisect_left(self.time_list, time_sec)
        if idx >= len(self.time_list):
            idx = len(self.time_list) - 1
        elif idx > 0 and abs(self.time_list[idx - 1] - time_sec) < abs(self.time_list[idx] - time_sec):
            idx = idx - 1

        matched_t = self.time_list[idx]
        return self.time_to_sats.get(matched_t, {}), self.time_to_dop.get(matched_t, {})

    def get_all_tracks(self):
        return self.all_sat_tracks
