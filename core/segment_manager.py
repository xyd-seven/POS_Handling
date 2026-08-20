# -*- coding: utf-8 -*-
"""
分段数据模型与后台解析调度模块
包含 LogParserThread 以及分段二分查找与时间范围解包逻辑。
"""
import os
from PySide6.QtCore import QThread, Signal
from gnss_parser import (BKStreamParser, parse_log_line, parse_bk_frame, 
                         unwrap_times, attach_rmc_speed_to_epochs)

class LogParserThread(QThread):
    progress_updated = Signal(int)
    finished_parsing = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, filepath, leap_secs, strict_checksum=False, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.leap_secs = leap_secs
        self.strict_checksum = strict_checksum
        self.is_cancelled = False

    def run(self):
        try:
            file_size = os.path.getsize(self.filepath)
            processed_size = 0
            file_epochs = []
            sentence_types = {}
            first_time_sec = None
            last_time_sec = None
            first_time_str = ''
            last_time_str = ''
            gga_status_events = []
            gsa_status_events = []
            last_time_sec_for_gsa = None
            last_emit_progress = -1

            parser = BKStreamParser()

            with open(self.filepath, 'rb') as f:
                while not self.is_cancelled:
                    chunk = f.read(65536)
                    if not chunk:
                        break

                    processed_size += len(chunk)
                    parser.feed(chunk)

                    while not self.is_cancelled:
                        res = parser.next_frame()
                        if res is None:
                            break

                        frame_type, frame_data = res
                        epoch = None

                        if frame_type == 'NMEA':
                            line = frame_data.decode('gbk', errors='replace')
                            comma_idx = line.find(',')
                            if comma_idx != -1:
                                stype = line[:comma_idx]
                                sentence_types[stype] = sentence_types.get(stype, 0) + 1
                            epoch = parse_log_line(line, self.leap_secs, self.strict_checksum)

                        elif frame_type == 'BK':
                            epoch = parse_bk_frame(frame_data)

                        if epoch:
                            if epoch['type'] in ['GGA', 'POGOS', 'PODRS', 'RMC', 'POSOL', 'BK_PNT_NAV']:
                                epoch['file_id'] = self.filepath
                                file_epochs.append(epoch)
                                last_time_sec_for_gsa = epoch['utc_time_sec']
                                if first_time_sec is None:
                                    first_time_sec = epoch['utc_time_sec']
                                    first_time_str = epoch['time_str']
                                last_time_sec = epoch['utc_time_sec']
                                last_time_str = epoch['time_str']

                                if epoch['type'] == 'GGA':
                                    gga_status_events.append((epoch['utc_time_sec'], {
                                        'quality': epoch['quality'],
                                        'num_sats': epoch['num_sats'],
                                        'hdop': epoch['hdop']
                                    }))
                            elif epoch['type'] == 'GSA' and last_time_sec_for_gsa is not None:
                                gsa_status_events.append((last_time_sec_for_gsa, {
                                    'vdop': epoch['vdop'],
                                    'pdop': epoch['pdop']
                                }))

                    progress = int((processed_size / file_size) * 100) if file_size > 0 else 0
                    if progress > last_emit_progress:
                        self.progress_updated.emit(progress)
                        last_emit_progress = progress

            if file_epochs:
                unwrapped = unwrap_times([ep['utc_time_sec'] for ep in file_epochs])
                for i, ep in enumerate(file_epochs):
                    ep['utc_time_sec'] = unwrapped[i]
                first_time_sec = file_epochs[0]['utc_time_sec']
                last_time_sec = file_epochs[-1]['utc_time_sec']

                def unwrap_status_events(events):
                    if not events:
                        return []
                    times = unwrap_times([item[0] for item in events])
                    return [(times[i], events[i][1]) for i in range(len(events))]

                gga_status_events = unwrap_status_events(gga_status_events)
                gsa_status_events = unwrap_status_events(gsa_status_events)

                gga_status_events.sort(key=lambda item: item[0])
                gsa_status_events.sort(key=lambda item: item[0])

                gga_idx = 0
                gsa_idx = 0
                n_gga = len(gga_status_events)
                n_gsa = len(gsa_status_events)

                for ep in file_epochs:
                    t = ep['utc_time_sec']

                    if ep['type'] in ['POGOS', 'PODRS'] and n_gga > 0:
                        while gga_idx < n_gga - 1 and gga_status_events[gga_idx][0] < t:
                            gga_idx += 1
                        best_fields = None
                        best_delta = 999.0
                        for idx in (gga_idx - 1, gga_idx):
                            if 0 <= idx < n_gga:
                                ev_t, fields = gga_status_events[idx]
                                delta = abs(ev_t - t)
                                if delta <= 1.0 and delta < best_delta:
                                    best_delta = delta
                                    best_fields = fields
                        if best_fields:
                            ep.update(best_fields)

                    if n_gsa > 0:
                        while gsa_idx < n_gsa - 1 and gsa_status_events[gsa_idx][0] < t:
                            gsa_idx += 1
                        best_fields = None
                        best_delta = 999.0
                        for idx in (gsa_idx - 1, gga_idx):
                            if 0 <= idx < n_gsa:
                                ev_t, fields = gsa_status_events[idx]
                                delta = abs(ev_t - t)
                                if delta <= 1.0 and delta < best_delta:
                                    best_delta = delta
                                    best_fields = fields
                        if best_fields:
                            ep.update(best_fields)

                file_epochs = attach_rmc_speed_to_epochs(file_epochs)

            self.progress_updated.emit(100)
            result = {
                'file_epochs': file_epochs,
                'first_time_sec': first_time_sec,
                'last_time_sec': last_time_sec,
                'first_time_str': first_time_str,
                'last_time_str': last_time_str,
                'sentence_types': sentence_types
            }
            self.finished_parsing.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
