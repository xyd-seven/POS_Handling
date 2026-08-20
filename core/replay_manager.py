# -*- coding: utf-8 -*-
"""
文件回放引擎与多线程快照调度模块
包含 ReplaySnapshotWorker 后台多线程解析器、切片快照、Seek LRU 缓存与高倍速节流控制。
"""
import os
import copy
from PySide6.QtCore import QThread, Signal
from gnss_parser import BKStreamParser, parse_log_line, parse_bk_frame, get_sat_info

class ReplaySnapshotWorker(QThread):
    sig_progress = Signal(int, bool, object, object)

    def __init__(self, generation, filepath, blocks, interval, leap_seconds):
        super().__init__()
        self.generation = generation
        self.filepath = filepath
        self.blocks = blocks
        self.interval = interval
        self.leap_seconds = leap_seconds
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        if not os.path.exists(self.filepath):
            self.sig_progress.emit(self.generation, True, [], {})
            return

        parser = BKStreamParser()
        gsv_satellites = {}
        used_satellites = set()
        sat_metadata = {}
        has_received_gsa = False
        latest_quality = 0
        latest_num_sats = 0
        latest_hdop = 1.0
        latest_pdop = 1.0

        raw_epochs = []
        snapshots = {}
        total_epochs_count = 0

        try:
            with open(self.filepath, 'rb') as f:
                for idx, (_, offset, length) in enumerate(self.blocks):
                    if not self.is_running:
                        break

                    f.seek(offset)
                    block_bytes = f.read(length)

                    parser.feed(block_bytes)
                    
                    while self.is_running:
                        res = parser.next_frame()
                        if res is None:
                            break
                        frame_type, frame_data = res

                        epoch = None
                        if frame_type == 'NMEA':
                            line_str = frame_data.decode('gbk', errors='replace')
                            epoch = parse_log_line(line_str, self.leap_seconds)
                            if epoch:
                                if epoch['type'] == 'GSV':
                                    prefix = epoch['prefix']
                                    total_msg = epoch['total_msg']
                                    msg_num = epoch['msg_num']
                                    signal_id = epoch['signal_id']

                                    if msg_num == 1:
                                        keys_to_remove = []
                                        for k in list(gsv_satellites.keys()):
                                            mapped_sys, _, _ = get_sat_info(prefix, k[1])
                                            if k[0] == mapped_sys:
                                                if signal_id in gsv_satellites[k]:
                                                    del gsv_satellites[k][signal_id]
                                                if not gsv_satellites[k]:
                                                    keys_to_remove.append(k)
                                        for k in keys_to_remove:
                                            gsv_satellites.pop(k, None)

                                    for sat in epoch['sats']:
                                        prn = sat['prn']
                                        snr = sat['snr']
                                        sys_prefix, real_prn, _ = get_sat_info(prefix, prn)
                                        key = (sys_prefix, real_prn)
                                        if key not in gsv_satellites:
                                            gsv_satellites[key] = {}
                                        gsv_satellites[key][signal_id] = snr

                                        elev = sat.get('elevation')
                                        azim = sat.get('azimuth')
                                        if key not in sat_metadata:
                                            sat_metadata[key] = {}
                                        if elev is not None:
                                            sat_metadata[key]['elevation'] = elev
                                        if azim is not None:
                                            sat_metadata[key]['azimuth'] = azim
                                else:
                                    if epoch['type'] in ['GGA', 'POSOL', 'BK_PNT_NAV']:
                                        used_satellites.clear()
                                        latest_quality = epoch.get('quality', 0)
                                        if 'num_sats' in epoch:
                                            latest_num_sats = epoch['num_sats']
                                        if 'hdop' in epoch:
                                            latest_hdop = epoch['hdop']
                                        if 'pdop' in epoch:
                                            latest_pdop = epoch['pdop']
                                        elif 'hdop' in epoch:
                                            latest_pdop = epoch['hdop']
                                    elif epoch['type'] == 'GSA':
                                        has_received_gsa = True
                                        sats_used = epoch.get('sats_used', [])
                                        sentence_type = epoch.get('sentence_type', '')
                                        talker = sentence_type[1:3] if len(sentence_type) >= 3 else ''

                                        gsa_prefix = None
                                        if talker == 'GP':
                                            gsa_prefix = 'GPS'
                                        elif talker in ['BD', 'GB']:
                                            gsa_prefix = 'BD'
                                        elif talker == 'GL':
                                            gsa_prefix = 'GL'
                                        elif talker == 'GA':
                                            gsa_prefix = 'GA'

                                        raw_line = epoch.get('raw_line', '')
                                        parts = [p.strip() for p in raw_line.split(',')]
                                        if talker == 'GN' and len(parts) > 18:
                                            sys_id = parts[18].split('*')[0].strip()
                                            if sys_id == '1':
                                                gsa_prefix = 'GPS'
                                            elif sys_id == '2':
                                                gsa_prefix = 'GL'
                                            elif sys_id == '3':
                                                gsa_prefix = 'GA'
                                            elif sys_id == '4':
                                                gsa_prefix = 'BD'

                                        for prn in sats_used:
                                            prn_prefix = gsa_prefix
                                            if prn_prefix is None:
                                                if 1 <= prn <= 32 or 193 <= prn <= 202:
                                                    prn_prefix = 'GPS'
                                                elif 65 <= prn <= 99:
                                                    prn_prefix = 'GL'
                                                elif 141 <= prn <= 172 or 1 <= prn <= 63:
                                                    prn_prefix = 'BD'
                                                else:
                                                    prn_prefix = 'GPS'

                                            if prn_prefix:
                                                sys_prefix, real_prn, _ = get_sat_info(prn_prefix, prn)
                                                used_satellites.add((sys_prefix, real_prn))

                                    elif epoch['type'] in ['POGOS', 'PODRS']:
                                        epoch['quality'] = latest_quality
                                        epoch['num_sats'] = latest_num_sats
                                        epoch['hdop'] = latest_hdop
                                        epoch['pdop'] = latest_pdop
                                    
                                    if epoch['type'] in ['GGA', 'POSOL', 'BK_PNT_NAV', 'POGOS', 'PODRS']:
                                        raw_epochs.append(epoch)
                                        total_epochs_count += 1

                        elif frame_type == 'BK':
                            epoch = parse_bk_frame(frame_data)
                            if epoch and epoch['type'] == 'BK_PNT_NAV':
                                used_satellites.clear()
                                latest_quality = epoch.get('quality', 0)
                                latest_num_sats = epoch.get('num_sats', 0)
                                latest_hdop = epoch.get('hdop', 1.0)
                                latest_pdop = epoch.get('pdop', 1.0)
                                raw_epochs.append(epoch)
                                total_epochs_count += 1

                    # 达到快照保存点
                    if idx % self.interval == 0:
                        snapshots[idx] = {
                            'serial_buffer': copy.deepcopy(parser),
                            'gsv_satellites': copy.deepcopy(gsv_satellites),
                            'used_satellites': set(used_satellites),
                            'sat_metadata': copy.deepcopy(sat_metadata),
                            'has_received_gsa': has_received_gsa,
                            'epochs_count': total_epochs_count,
                            'latest_quality': latest_quality,
                            'latest_num_sats': latest_num_sats,
                            'latest_hdop': latest_hdop,
                            'latest_pdop': latest_pdop
                        }

                    # 分批发送解析结果
                    if (idx > 0 and idx % 100 == 0) or idx == len(self.blocks) - 1:
                        self.sig_progress.emit(self.generation, False, raw_epochs, snapshots)
                        raw_epochs = []
                        snapshots = {}

                    # 每 50 块释放一次 GIL
                    if idx % 50 == 0:
                        self.msleep(1)

        except Exception as e:
            print(f"Background snapshot worker error: {e}")
        
        self.sig_progress.emit(self.generation, True, raw_epochs, snapshots)
