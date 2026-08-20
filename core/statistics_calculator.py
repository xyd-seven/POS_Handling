# -*- coding: utf-8 -*-
"""
GNSS 定位精度指标计算模块 (Accuracy Metrics Calculator)
严格按照大地测量与导航统计学规范，计算包含明确置信度百分比的定位精度指标。
"""
import numpy as np

def compute_accuracy_metrics(e_err, n_err, u_err=None):
    """
    计算完整的 GNSS 定位精度指标
    
    参数:
        e_err (array-like): 东向误差 (米)
        n_err (array-like): 北向误差 (米)
        u_err (array-like, optional): 高程误差 (米)
        
    返回:
        dict: 包含各项指标计算结果与格式化字符串的字典
    """
    if e_err is None or len(e_err) == 0 or n_err is None or len(n_err) == 0:
        return _empty_metrics()
        
    e = np.asarray(e_err, dtype=np.float64)
    n = np.asarray(n_err, dtype=np.float64)
    
    # 过滤无效 NaN / Inf
    valid_mask = np.isfinite(e) & np.isfinite(n)
    if u_err is not None:
        u = np.asarray(u_err, dtype=np.float64)
        valid_mask &= np.isfinite(u)
    else:
        u = np.zeros_like(e)
        
    e = e[valid_mask]
    n = n[valid_mask]
    u = u[valid_mask]
    
    N = len(e)
    if N == 0:
        return _empty_metrics()
        
    # 计算水平 2D 误差与三维 3D 误差
    d_2d = np.sqrt(e**2 + n**2)
    d_3d = np.sqrt(e**2 + n**2 + u**2)
    
    # 1. 水平 2D 指标
    cep_50 = float(np.percentile(d_2d, 50))
    rms_2d_68 = float(np.sqrt(np.mean(d_2d**2)))
    r95_95 = float(np.percentile(d_2d, 95))
    drms_2_98 = 2.0 * rms_2d_68
    cep_99 = float(np.percentile(d_2d, 99))
    max_2d = float(np.max(d_2d))
    
    # 2. 单向与三维指标
    rms_e = float(np.sqrt(np.mean(e**2)))
    rms_n = float(np.sqrt(np.mean(n**2)))
    rms_u_68 = float(np.sqrt(np.mean(u**2))) if u_err is not None else 0.0
    rms_3d_68 = float(np.sqrt(np.mean(d_3d**2))) if u_err is not None else rms_2d_68
    sep_95 = float(np.percentile(d_3d, 95)) if u_err is not None else r95_95
    max_3d = float(np.max(d_3d)) if u_err is not None else max_2d
    
    return {
        'count': N,
        'cep_50': cep_50,
        'rms_2d_68': rms_2d_68,
        'r95_95': r95_95,
        'drms_2_98': drms_2_98,
        'cep_99': cep_99,
        'max_2d': max_2d,
        'rms_e': rms_e,
        'rms_n': rms_n,
        'rms_u_68': rms_u_68,
        'rms_3d_68': rms_3d_68,
        'sep_95': sep_95,
        'max_3d': max_3d
    }

def _empty_metrics():
    return {
        'count': 0,
        'cep_50': 0.0,
        'rms_2d_68': 0.0,
        'r95_95': 0.0,
        'drms_2_98': 0.0,
        'cep_99': 0.0,
        'max_2d': 0.0,
        'rms_e': 0.0,
        'rms_n': 0.0,
        'rms_u_68': 0.0,
        'rms_3d_68': 0.0,
        'sep_95': 0.0,
        'max_3d': 0.0
    }
