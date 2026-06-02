#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_skin_spec.py
功能：實現 SkinSpec Island 地形皮層合約的離線靜態語意校驗器 (Linter)。
特點：
1. 零動態執行 (Zero-Eval/Exec)：純文字處理與 AST 靜態屬性校驗。
2. Ingestion 預校驗：在編譯成 JSON 之前，先期阻斷不合規的合約宣告。
3. 極限精密化：整合 Caret Trace 錯誤回溯與精確列級診斷輸出。
"""

import os
import sys
import argparse
from parse_skin_spec import parse_code, format_error_trace

def inspect_manifest_ast(ast, code=None):
    """靜態語意校驗器核心：實施七大 Ingestion 預檢規則，支援 Caret Trace 錯誤定位"""
    _meta = ast.get("_meta", {})

    # 1. 驗證 schema 合規性
    schema = ast.get("schema")
    if not schema:
        raise ValueError("[LINTER ERROR] 缺失必需的 schema 宣告！")
    if schema != "rrkal.renderer_skin_asset.v0.2.2":
        msg = f"[LINTER ERROR] 不支援的 schema 規格版本: '{schema}' (必須為 rrkal.renderer_skin_asset.v0.2.2)"
        if code and "schema" in _meta:
            line, col = _meta["schema"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)

    # 2. 驗證緯度 bounds 合理性
    bounds = ast.get("bounds")
    if not bounds:
        raise ValueError("[LINTER ERROR] 缺失 bounds 邊界宣告！")
    
    lat_min = bounds.get("lat_min")
    lat_max = bounds.get("lat_max")
    if lat_min is None or lat_max is None:
        raise ValueError("[LINTER ERROR] bounds 缺失 lat 經度參數")
        
    if not (-90.0 <= lat_min <= 90.0) or not (-90.0 <= lat_max <= 90.0):
        msg = f"[LINTER ERROR] 網格緯度範圍非法：[{lat_min}, {lat_max}] (緯度 bounds 必須嚴格在 [-90.0, 90.0] 內)"
        if code and "bounds" in _meta:
            line, col = _meta["bounds"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)
        
    if lat_min > lat_max:
        msg = f"[LINTER ERROR] 網格緯度順序非法：lat_min ({lat_min}) 大於 lat_max ({lat_max})"
        if code and "bounds" in _meta:
            line, col = _meta["bounds"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)

    # 3. 驗證經度 bounds 合理性
    lon_min = bounds.get("lon_min")
    lon_max = bounds.get("lon_max")
    if lon_min is None or lon_max is None:
        raise ValueError("[LINTER ERROR] bounds 缺失 lon 緯度參數")
        
    if not (-180.0 <= lon_min <= 180.0) or not (-180.0 <= lon_max <= 180.0):
        msg = f"[LINTER ERROR] 網格經度範圍非法：[{lon_min}, {lon_max}] (經度 bounds 必須嚴格在 [-180.0, 180.0] 內)"
        if code and "bounds" in _meta:
            line, col = _meta["bounds"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)
        
    if lon_min > lon_max:
        msg = f"[LINTER ERROR] 網格經度順序非法：lon_min ({lon_min}) 大於 lon_max ({lon_max})"
        if code and "bounds" in _meta:
            line, col = _meta["bounds"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)

    # 4. 驗證 encoding 量化步長
    encoding = ast.get("encoding")
    if not encoding:
        raise ValueError("[LINTER ERROR] 缺失 encoding 量化參數宣告！")
    scale = encoding.get("scale")
    if scale is None:
        raise ValueError("[LINTER ERROR] encoding 缺失 scale 參數")
    if scale <= 0.0:
        msg = f"[LINTER ERROR] encoding 量化步長 scale 非法: {scale} (scale 必須嚴格大於 0.0)"
        if code and "encoding_scale" in _meta:
            line, col = _meta["encoding_scale"]
            msg = format_error_trace(code, line, col, msg)
        elif code and "encoding" in _meta:
            line, col = _meta["encoding"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)

    # 5. 驗證 levels 金字塔層級連續性
    levels = ast.get("levels", [])
    if not levels:
        raise ValueError("[LINTER ERROR] levels 金字塔宣告為空，必須至少宣告 level 0！")
        
    lvl_nums = [lvl.get("level") for lvl in levels]
    # 確保層級不重複
    if len(lvl_nums) != len(set(lvl_nums)):
        raise ValueError(f"[LINTER ERROR] 檢測到重複的 level 宣告: {lvl_nums}")
        
    # 排序並檢查連續性（必須從 0 開始且嚴格遞增 1）
    sorted_lvls = sorted(lvl_nums)
    expected_lvls = list(range(len(sorted_lvls)))
    if sorted_lvls != expected_lvls:
        msg = f"[LINTER ERROR] 金字塔層級順序不連續！實際: {sorted_lvls}，預期: {expected_lvls} (必須從 level 0 開始且層級嚴格連續)"
        # 尋找第一個不連續的 level
        if code and levels:
            first_lvl_meta = levels[0].get("_meta", {})
            if "level_num" in first_lvl_meta:
                line, col = first_lvl_meta["level_num"]
                msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)

    # 6. 驗證各 levels 內部尺寸與細胞合理性
    for lvl_info in levels:
        lvl = lvl_info.get("level")
        h, w = lvl_info.get("shape", [0, 0])
        cell_size = lvl_info.get("cell_size_deg")
        path = lvl_info.get("path")
        lvl_meta = lvl_info.get("_meta", {})

        if not path:
            raise ValueError(f"[LINTER ERROR] LOD {lvl} 缺失 elevation payload 路徑路引！")
        if h <= 0 or w <= 0:
            msg = f"[LINTER ERROR] LOD {lvl} 的 shape [{h}, {w}] 非法 (網格高寬各維度必須大於 0)"
            if code and "shape" in lvl_meta:
                line, col = lvl_meta["shape"]
                msg = format_error_trace(code, line, col, msg)
            raise ValueError(msg)
        if cell_size is None:
            raise ValueError(f"[LINTER ERROR] LOD {lvl} 缺失 cell_size_deg 宣告")
        if cell_size <= 0.0:
            msg = f"[LINTER ERROR] LOD {lvl} 的 cell_size_deg ({cell_size}) 非法 (cell_size_deg 必須大於 0.0)"
            if code and "cell_size_deg" in lvl_meta:
                line, col = lvl_meta["cell_size_deg"]
                msg = format_error_trace(code, line, col, msg)
            raise ValueError(msg)

    return True

def inspect_skin_spec_file(filepath):
    """讀取檔案並執行靜態語意校驗"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[ERROR] 找不到待校驗之檔案: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
        
    ast = parse_code(code)
    return inspect_manifest_ast(ast, code=code)

def main():
    parser = argparse.ArgumentParser(description="SkinSpec Island 靜態語意校驗器 (Linter)")
    parser.add_argument("-i", "--input", required=True, help="待校驗之 DSL 原始檔 (.skinisland)")
    args = parser.parse_args()

    try:
        inspect_skin_spec_file(args.input)
        print(f"[+] 靜態語意校驗成功！檔案 [{args.input}] 完全符合 Ingestion 預檢規範。")
        sys.exit(0)
    except Exception as e:
        print(f"[X] 靜態校驗失敗:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
