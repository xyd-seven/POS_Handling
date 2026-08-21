# -*- coding: utf-8 -*-
"""
Local MBTiles Tile Server (Zero External Dependencies)
Uses Python standard library sqlite3 and http.server.ThreadingHTTPServer.
Serves offline raster tiles (PNG, JPG, WEBP) to Leaflet.js WebGIS.
Supports automatic TMS-to-XYZ coordinate conversion, bounding box extraction, and dynamic package switching.
"""

import os
import sqlite3
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MBTilesTileHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 禁用请求日志输出以保持终端清爽
        pass

    def do_GET(self):
        server_inst = getattr(self.server, 'mbtiles_server', None)
        if not server_inst:
            self.send_response(500)
            self.end_headers()
            return

        path = self.path.split('?')[0]

        if path == '/meta':
            meta = server_inst.get_metadata()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(meta, ensure_ascii=False).encode('utf-8'))
            return

        # /tiles/{z}/{x}/{y} or /tiles/{z}/{x}/{y}.png
        if path.startswith('/tiles/'):
            parts = path.strip('/').split('/')
            if len(parts) >= 4:
                try:
                    z = int(parts[1])
                    x = int(parts[2])
                    y_str = parts[3].split('.')[0]
                    y = int(y_str)

                    tile_bytes, content_type = server_inst.get_tile(z, x, y)
                    if tile_bytes:
                        self.send_response(200)
                        self.send_header('Content-Type', content_type)
                        self.send_header('Cache-Control', 'public, max-age=86400')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(tile_bytes)
                        return
                except Exception:
                    pass

        # 瓦片不存在或未命中
        self.send_response(404)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()


class MBTilesServer:
    def __init__(self, host='127.0.0.1', port=0):
        self.host = host
        self.port = port
        self.current_file = None
        self.metadata = {}
        self.lock = threading.Lock()
        self.server = None
        self.thread = None

        self._start_server()

    def _start_server(self):
        try:
            self.server = ThreadedHTTPServer((self.host, self.port), MBTilesTileHandler)
            self.server.mbtiles_server = self
            self.port = self.server.server_address[1]
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f'Error starting MBTilesServer: {e}')

    def load_mbtiles(self, filepath):
        """
        加载或切换指定的 .mbtiles 离线文件
        """
        if not filepath or not os.path.isfile(filepath):
            return False

        with self.lock:
            try:
                conn = sqlite3.connect(filepath)
                cursor = conn.cursor()

                meta = {'name': os.path.basename(filepath), 'bounds': None, 'minzoom': 0, 'maxzoom': 18, 'format': 'png'}
                try:
                    cursor.execute("SELECT name, value FROM metadata")
                    for row in cursor.fetchall():
                        key = str(row[0]).lower()
                        meta[key] = row[1]
                except Exception:
                    pass

                if 'bounds' in meta and isinstance(meta['bounds'], str):
                    try:
                        b_parts = [float(x.strip()) for x in meta['bounds'].split(',')]
                        if len(b_parts) == 4:
                            meta['parsed_bounds'] = {
                                'minLon': b_parts[0], 'minLat': b_parts[1],
                                'maxLon': b_parts[2], 'maxLat': b_parts[3]
                            }
                    except Exception:
                        pass

                conn.close()

                self.current_file = filepath
                self.metadata = meta
                return True
            except Exception as e:
                print(f'Failed to load MBTiles {filepath}: {e}')
                return False

    def get_tile(self, z, x, y):
        """
        从 SQLite 中提取瓦片数据 (TMS 规范 y_tms = 2^z - 1 - y, 兼顾标准 XYZ)
        """
        if not self.current_file:
            return None, 'image/png'

        tms_y = (1 << z) - 1 - y

        try:
            conn = sqlite3.connect(f'file:{self.current_file}?mode=ro', uri=True)
            cursor = conn.cursor()

            # 1. 尝试 TMS 查询
            cursor.execute("SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?", (z, x, tms_y))
            row = cursor.fetchone()

            # 2. 回退尝试原生 XYZ 查询
            if not row:
                cursor.execute("SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?", (z, x, y))
                row = cursor.fetchone()

            conn.close()

            if row and row[0]:
                tile_bytes = bytes(row[0])
                if tile_bytes.startswith(b'\x89PNG'):
                    content_type = 'image/png'
                elif tile_bytes.startswith(b'\xff\xd8'):
                    content_type = 'image/jpeg'
                elif tile_bytes.startswith(b'RIFF') and b'WEBP' in tile_bytes[:12]:
                    content_type = 'image/webp'
                else:
                    content_type = 'image/png'
                return tile_bytes, content_type
        except Exception:
            pass

        return None, 'image/png'

    def get_metadata(self):
        with self.lock:
            return dict(self.metadata)

    def get_tile_url_template(self):
        return f'http://127.0.0.1:{self.port}/tiles/{{z}}/{{x}}/{{y}}.png'

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
