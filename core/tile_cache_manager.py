# -*- coding: utf-8 -*-
"""
Local Tile Cache Manager & Embedded Proxy Service
Provides persistent disk caching for online map tiles (Tianditu, AMap, OSM, etc.),
bypasses Tianditu 403 Forbidden restrictions using dedicated client User-Agent,
and serves tiles to QWebEngineView via a lightweight local HTTP proxy.
"""

import os
import sys
import time
import random
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# 1x1 透明 PNG 瓦片数据 (在离线无网络且未缓存时安全返回，防止前端报错)
TRANSPARENT_1X1_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05'
    b'\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)

class TileProxyHTTPHandler(BaseHTTPRequestHandler):
    """ 处理 Leaflet 前端发起的瓦片请求 /tile/{source}/{z}/{x}/{y} """
    
    def log_message(self, format, *args):
        # 屏蔽高频静态瓦片请求的标准访问日志，避免控制台刷屏
        pass

    def do_GET(self):
        try:
            parts = self.path.strip('/').split('?')[0].split('/')
            if len(parts) >= 5 and parts[0] == 'tile':
                source_key = parts[1]
                z = int(parts[2])
                x = int(parts[3])
                y = int(parts[4])
                
                manager = TileCacheManager()
                data, content_type = manager.get_tile(source_key, z, x, y)
                
                if data:
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'public, max-age=2592000') # 缓存 30 天
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                else:
                    # 离线或未命中，返回 1x1 透明 PNG
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Content-Length', str(len(TRANSPARENT_1X1_PNG)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(TRANSPARENT_1X1_PNG)
                    return

            self.send_response(404)
            self.end_headers()
        except Exception:
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass


class TileCacheManager:
    """ 本地瓦片缓存单例管理器 """
    _instance = None
    _lock = threading.Lock()

    # 内置图源模板与参数定义 (所有天地图请求均带 tk 且用非 Mozilla 客户端请求头下载)
    SOURCES = {
        # 天地图影像底图
        'tdt_sat': {
            'url': 'https://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
            'subdomains': ['0', '1', '2', '3', '4', '5', '6', '7'],
            'content_type': 'image/jpeg'
        },
        # 天地图影像注记
        'tdt_sat_annot': {
            'url': 'https://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
            'subdomains': ['0', '1', '2', '3', '4', '5', '6', '7'],
            'content_type': 'image/png'
        },
        # 天地图矢量底图
        'tdt_vec': {
            'url': 'https://t{s}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
            'subdomains': ['0', '1', '2', '3', '4', '5', '6', '7'],
            'content_type': 'image/png'
        },
        # 天地图矢量注记
        'tdt_vec_annot': {
            'url': 'https://t{s}.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8e50f8cdd0450027d98d635238363e11',
            'subdomains': ['0', '1', '2', '3', '4', '5', '6', '7'],
            'content_type': 'image/png'
        },
        # 高德矢量底图
        'amap_vec': {
            'url': 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
            'subdomains': ['1', '2', '3', '4'],
            'content_type': 'image/png'
        },
        # 高德卫星底图
        'amap_sat': {
            'url': 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
            'subdomains': ['1', '2', '3', '4'],
            'content_type': 'image/jpeg'
        },
        # 高德卫星注记
        'amap_sat_annot': {
            'url': 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}',
            'subdomains': ['1', '2', '3', '4'],
            'content_type': 'image/png'
        },
        # OpenStreetMap
        'osm': {
            'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'subdomains': ['a', 'b', 'c'],
            'content_type': 'image/png'
        }
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TileCacheManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        
        # 1. 确定缓存根路径: 位于程序所在目录同级 ./tile_cache/ (随程序走，不占 C 盘)
        if getattr(sys, 'frozen', False):
            # 打包运行环境 (onedir: exe 同级目录)
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # 源码运行环境
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.cache_root = os.path.join(app_dir, "tile_cache")
        try:
            os.makedirs(self.cache_root, exist_ok=True)
        except Exception:
            pass

        # 2. 初始化嵌入式 HTTP 服务
        self.port = 0
        self.httpd = None
        self.server_thread = None
        self.is_running = False
        self.start_server()

    def get_cache_root(self):
        return self.cache_root

    def start_server(self):
        """ 启动本地嵌入式轻量 HTTP 代理服务 (绑定 127.0.0.1 动态端口) """
        if self.is_running:
            return self.port
            
        try:
            # 绑定 127.0.0.1:0 由 OS 自动分发空闲可用端口，绝对不冲突
            self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), TileProxyHTTPHandler)
            self.port = self.httpd.server_address[1]
            self.is_running = True
            
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
            print(f"[TileCacheManager] Local tile proxy server running on http://127.0.0.1:{self.port}, cache dir: {self.cache_root}")
        except Exception as e:
            print(f"[TileCacheManager] Failed to start local proxy: {e}")
            self.port = 0
            self.is_running = False
            
        return self.port

    def stop_server(self):
        if self.httpd and self.is_running:
            self.is_running = False
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass

    def get_tile_url_template(self, source_key):
        """ 返回提供给 Leaflet L.tileLayer 使用的本地代理 URL 模板 """
        if self.port > 0:
            return f"http://127.0.0.1:{self.port}/tile/{source_key}/{{z}}/{{x}}/{{y}}"
        # 降级回退
        cfg = self.SOURCES.get(source_key, {})
        return cfg.get('url', '')

    def get_tile(self, source_key, z, x, y):
        """
        获取单张瓦片数据：
        1. 检查本地磁盘持久化缓存，若存在则直接返回 (1ms)；
        2. 若不存在，使用合规客户端 UA (无 Mozilla/5.0) 从互联网拉取，自动写入磁盘缓存并返回。
        """
        cfg = self.SOURCES.get(source_key)
        if not cfg:
            return None, 'image/png'

        tile_dir = os.path.join(self.cache_root, source_key, str(z), str(x))
        tile_file = os.path.join(tile_dir, f"{y}.dat")

        # 1. 命中本地持久化缓存
        if os.path.exists(tile_file):
            try:
                with open(tile_file, 'rb') as f:
                    data = f.read()
                if len(data) > 0:
                    return data, cfg['content_type']
            except Exception:
                pass

        # 2. 未命中，在线下载 (使用合规专有客户端 User-Agent，彻底规避天地图 403)
        subdomain = random.choice(cfg['subdomains'])
        remote_url = cfg['url'].format(s=subdomain, z=z, x=x, y=y)

        # 核心防拦截请求头：使用纯客户端专有 UA，绝不带 Mozilla/5.0
        headers = {
            'User-Agent': 'GNSS_Precision_Tool/1.0',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
        }

        try:
            req = urllib.request.Request(remote_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    data = resp.read()
                    # 校验是否为合法图片数据 (天地图有时在出错时仍返回 200 JSON 错误信息)
                    if len(data) > 300 and not data.startswith(b'{"'):
                        # 自动持久化落盘
                        try:
                            os.makedirs(tile_dir, exist_ok=True)
                            with open(tile_file, 'wb') as f:
                                f.write(data)
                        except Exception:
                            pass
                        return data, cfg['content_type']
        except Exception:
            pass

        return None, cfg['content_type']

    def get_cache_size_mb(self):
        """ 统计当前本地缓存瓦片总容量 (MB) """
        total_bytes = 0
        if os.path.exists(self.cache_root):
            for root, _, files in os.walk(self.cache_root):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_bytes += os.path.getsize(fp)
                    except Exception:
                        pass
        return round(total_bytes / (1024 * 1024), 2)

    def clear_cache(self):
        """ 清空所有本地缓存瓦片 """
        import shutil
        if os.path.exists(self.cache_root):
            try:
                shutil.rmtree(self.cache_root, ignore_errors=True)
                os.makedirs(self.cache_root, exist_ok=True)
                return True
            except Exception:
                return False
        return True
