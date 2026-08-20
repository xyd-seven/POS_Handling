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

    def build_from_file_data(self, gsv_events, file_epochs, gsa_events=None):
        """
        从解析得到的 GSV 序列、定位历元及 GSA 状态构建天空图模型
        """
        self.clear()
        if not gsv_events and not file_epochs:
            return

        # 1. 建立 GSA/GGA 在用卫星表与 DOP 表: time_sec -> used_sat_set & dop_info
        time_to_used = {}
        time_to_dop_map = {}

        for ep in file_epochs:
            t = ep.get('utc_time_sec')
            if t is None:
                continue
            time_to_dop_map[t] = {
                'pdop': float(ep.get('pdop', 1.0) if ep.get('pdop') is not None else 1.0),
                'hdop': float(ep.get('hdop', 1.0) if ep.get('hdop') is not None else 1.0),
                'vdop': float(ep.get('vdop', 1.0) if ep.get('vdop') is not None else 1.0),
                'num_sats': int(ep.get('num_sats', 0)),
                'quality': int(ep.get('quality', 0))
            }

        if gsa_events:
            for ev_t, fields in gsa_events:
                if ev_t is None:
                    continue
                if ev_t not in time_to_used:
                    time_to_used[ev_t] = set()
                sats_used = fields.get('sats_used', [])
                sentence_type = fields.get('sentence_type', '')
                talker = sentence_type[1:3] if len(sentence_type) >= 3 else ''
                gsa_prefix = None
                if talker == 'GP': gsa_prefix = 'GPS'
                elif talker in ['BD', 'GB']: gsa_prefix = 'BD'
                elif talker == 'GL': gsa_prefix = 'GL'
                elif talker == 'GA': gsa_prefix = 'GA'

                for prn in sats_used:
                    prn_prefix = gsa_prefix
                    if prn_prefix is None:
                        if 1 <= prn <= 32 or 193 <= prn <= 202: prn_prefix = 'GPS'
                        elif 65 <= prn <= 99: prn_prefix = 'GL'
                        elif 141 <= prn <= 172 or 1 <= prn <= 63: prn_prefix = 'BD'
                        else: prn_prefix = 'GPS'
                    sys_prefix, real_prn, _ = get_sat_info(prn_prefix, prn)
                    time_to_used[ev_t].add((sys_prefix, real_prn))

        # 2. 遍历 GSV 帧构建卫星时序图
        current_sats = {}
        for gsv in gsv_events:
            t = gsv.get('utc_time_sec')
            if t is None:
                continue

            prefix = gsv.get('prefix', '')
            msg_num = gsv.get('msg_num', 1)

            if msg_num == 1:
                keys_to_del = [k for k in current_sats if k[0] == prefix]
                for k in keys_to_del:
                    del current_sats[k]

            used_set = time_to_used.get(t, set())

            for s in gsv.get('sats', []):
                prn = s.get('prn')
                elev = s.get('elevation')
                azim = s.get('azimuth')
                snr = s.get('snr', 0)
                if prn is None or elev is None or azim is None:
                    continue
                
                # 过滤无效哑数据（仰角和方位角均为0的未解算点）
                if elev <= 0.01 and azim <= 0.01:
                    continue
                if not (0 <= elev <= 90 and 0 <= azim <= 360):
                    continue

                sys_prefix, real_prn, lbl_char = get_sat_info(prefix, prn)
                sat_key = (sys_prefix, real_prn)
                is_used = sat_key in used_set

                current_sats[sat_key] = {
                    'sys_prefix': sys_prefix,
                    'prn': real_prn,
                    'lbl_char': lbl_char,
                    'elevation': float(elev),
                    'azimuth': float(azim),
                    'snr': float(snr),
                    'is_used': is_used
                }

                # 记录星轨点
                if sat_key not in self.all_sat_tracks:
                    self.all_sat_tracks[sat_key] = []
                self.all_sat_tracks[sat_key].append((t, float(elev), float(azim), is_used))

            # 存储快照
            if t not in self.time_to_sats:
                self.time_list.append(t)
            self.time_to_sats[t] = {k: dict(v) for k, v in current_sats.items()}
            self.time_to_dop[t] = time_to_dop_map.get(t, {'pdop': 1.0, 'hdop': 1.0, 'vdop': 1.0, 'num_sats': len(current_sats), 'quality': 4})

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
