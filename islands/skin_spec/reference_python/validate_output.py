#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_output.py
功能：對編譯產出的 JSON 進行結構化 Ingestion 聯鎖校驗，斷言其符合 v0.2.2 規格。
特點：
1. 零實體數據依賴：純粹對 JSON 結構進行 schema 與 limits 欄位約束檢測。
2. 閉環保證：確保由 islands DSL 生成的成果與 vis_2_dis Ingestion 網關標準 100% 對齊。
"""

import os
import json
import re

def validate_generated_manifest(json_path):
    """聯鎖校驗生成出的 manifest JSON 是否合規"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"[ERROR] 找不到待校驗之 JSON 契約: {json_path}")
        
    with open(json_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    print(f"[*] 正在對生成之契約進行結構化 Ingestion 聯鎖校驗: {json_path}")
    
    # 1. 斷言 schema 版本為 v0.2.2
    schema = manifest.get("schema")
    if schema != "rrkal.renderer_skin_asset.v0.2.2":
        raise ValueError(f"[SPEC ERROR] 不支援的 schema 規格版本: {schema}")
        
    # 2. 斷言基本宣告
    kind = manifest.get("kind")
    if kind != "terrain":
        raise ValueError(f"[SPEC ERROR] 非地形皮層: {kind}")
        
    status = manifest.get("status")
    if status != "ready":
        raise ValueError(f"[SPEC ERROR] 狀態非法: {status}")
        
    source_fingerprint = manifest.get("source_fingerprint", "")
    if not re.match(r"^sha256:[a-fA-F0-9]{64}$", source_fingerprint):
        raise ValueError(f"[SPEC ERROR] source_fingerprint 格式非法: {source_fingerprint}")
        
    # 3. 驗證 grid 座標對齊
    grid = manifest.get("grid", {})
    if grid.get("row_order") != "south_to_north":
        raise ValueError(f"[SPEC ERROR] row_order 座標對齊規格非法: {grid.get('row_order')}")
    if grid.get("col_order") != "west_to_east":
        raise ValueError(f"[SPEC ERROR] col_order 座標對齊規格非法: {grid.get('col_order')}")
        
    # 4. 驗證 encoding 量化參數
    encoding = manifest.get("encoding", {})
    if encoding.get("type") != "int16_meter":
        raise ValueError(f"[SPEC ERROR] 量化編碼型態非法: {encoding.get('type')}")
    if not isinstance(encoding.get("scale"), (int, float)):
        raise ValueError(f"[SPEC ERROR] 量化步長 scale 缺失或非法")
        
    # 5. 驗證 levels 金字塔層級結構與 limits 約束
    limits = manifest.get("limits", {})
    max_levels = limits.get("max_levels", 12)
    
    levels = manifest.get("levels", [])
    if not levels:
        raise ValueError("[SPEC ERROR] levels 金字塔資料為空")
    if len(levels) > max_levels:
        raise ValueError(f"[SPEC ERROR] 金字塔層級數量超出上限")
        
    checksums = manifest.get("checksums", {})
    
    for lvl_info in levels:
        lvl = lvl_info.get("level")
        h, w = lvl_info.get("shape", [0, 0])
        raw_nbytes = lvl_info.get("raw_nbytes")
        
        # 內存 sizes 校驗公式：raw_nbytes 必須嚴格等於 height * width * 2 (int16 雙位元組)
        expected_raw_nbytes = h * w * 2
        if raw_nbytes != expected_raw_nbytes:
            raise ValueError(f"[SPEC ERROR] LOD {lvl} 的 raw_nbytes ({raw_nbytes}) 與公式預期 ({expected_raw_nbytes}) 不符！")
            
        # 校驗 minmax 宣告為 global_lod_summary
        minmax_scope = lvl_info.get("minmax_scope")
        if minmax_scope != "global_lod_summary":
            raise ValueError(f"[SPEC ERROR] LOD {lvl} 的 minmax 範圍性質非法: {minmax_scope}")
            
        # 驗證 path 與 coverage keys 是否註冊在 checksums 字典中
        for path_key in ["path", "valid_mask", "land_fraction", "water_fraction", "minmax_path"]:
            path_val = lvl_info.get(path_key)
            if not path_val:
                raise ValueError(f"[SPEC ERROR] LOD {lvl} 缺失必需的 path 參數: {path_key}")
            if path_val not in checksums:
                raise ValueError(f"[SPEC ERROR] 檔案 [{path_val}] 未在頂層 checksums 字典中註冊指紋")
                
    print("[+] 恭喜！該編譯產出之 JSON 契約完全通過 v0.2.2 結構化 Ingestion 聯鎖校驗！")
    return True

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 預設校驗 examples 下的 terrain_synthetic.expected.json
    sample_path = os.path.abspath(os.path.join(current_dir, "..", "examples", "terrain_synthetic.expected.json"))
    
    try:
        validate_generated_manifest(sample_path)
    except Exception as e:
        print(f"\n[X] 聯鎖校驗失敗: {e}")
