#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_layer_spec.py
功能：手寫 LayerSpec DSL AST 的靜態語意校驗器 (Linter)。
特點：
1. 零動態指令執行，完全進行靜態屬性安全防護。
2. Ingestion 預檢規則健全。
3. 極限精密化：整合 Caret Trace 錯誤回溯與精確列級診斷輸出。
"""

import os
import sys
import argparse
from parse_layer_spec import parse_layer_code, format_error_trace

# 合法混合模式定義
VALID_BLEND_MODES = {"normal", "screen", "multiply", "overlay", "soft_light", "soft light"}

def inspect_layer_manifest_ast(ast, code=None):
    """靜態校驗圖層規格 AST 的合理性與邏輯完整度，支援 Caret Trace 錯誤定位"""
    _meta = ast.get("_meta", {})
    
    # 1. 校驗 Schema 版本
    schema = ast.get("schema")
    if not schema:
        raise ValueError("[LINTER ERROR] 欄位缺失：必須指定 schema 版本。")
    if schema != "rrkal_displaytools.render_layer_spec.v0.2.1":
        msg = f"[LINTER ERROR] schema 版本錯誤：必須為 'rrkal_displaytools.render_layer_spec.v0.2.1'，得到 '{schema}'。"
        if code and "schema" in _meta:
            line, col = _meta["schema"]
            msg = format_error_trace(code, line, col, msg)
        raise ValueError(msg)
        
    # 2. 校驗不透明度 (opacity) 範圍
    opacity = ast.get("opacity")
    if opacity is not None:
        if not isinstance(opacity, (int, float)):
            msg = f"[LINTER ERROR] opacity 必須為數值型態，得到 '{type(opacity).__name__}'。"
            if code and "opacity" in _meta:
                line, col = _meta["opacity"]
                msg = format_error_trace(code, line, col, msg)
            raise ValueError(msg)
        if opacity < 0.0 or opacity > 1.0:
            msg = f"[LINTER ERROR] opacity 越界：必須在 [0.0, 1.0] 之間，得到 '{opacity}'。"
            if code and "opacity" in _meta:
                line, col = _meta["opacity"]
                msg = format_error_trace(code, line, col, msg)
            raise ValueError(msg)
            
    # 3. 校驗混合模式 (blend_mode)
    blend_mode = ast.get("blend_mode")
    if blend_mode is not None:
        if not isinstance(blend_mode, str):
            raise ValueError("[LINTER ERROR] blend_mode 必須為字串。")
        if blend_mode.lower() not in VALID_BLEND_MODES:
            msg = f"[LINTER ERROR] 未知混合模式 '{blend_mode}'：合法清單為 {VALID_BLEND_MODES}。"
            if code and "blend_mode" in _meta:
                line, col = _meta["blend_mode"]
                msg = format_error_trace(code, line, col, msg)
            raise ValueError(msg)
            
    # 4. 校驗 LOD 策略 (lod_policy)
    lod = ast.get("lod_policy", {})
    if lod:
        lod_params_meta = _meta.get("lod_policy_params", {})
        for level_key in ["interactive_level", "preview_level", "quality_level", "export_level"]:
            val = lod.get(level_key)
            if val is not None:
                if not isinstance(val, int) or val < 0:
                    msg = f"[LINTER ERROR] lod_policy 欄位 '{level_key}' 非法：必須是大於或等於 0 的整數，得到 '{val}'。"
                    if code and level_key in lod_params_meta:
                        line, col = lod_params_meta[level_key]
                        msg = format_error_trace(code, line, col, msg)
                    elif code and "lod_policy" in _meta:
                        line, col = _meta["lod_policy"]
                        msg = format_error_trace(code, line, col, msg)
                    raise ValueError(msg)
                    
    # 5. 校驗圖層遮蔽門檻 (opaque_mask.threshold)
    cov = ast.get("coverage", {})
    if cov:
        opaque = cov.get("opaque_mask", {})
        if opaque:
            threshold = opaque.get("threshold")
            if threshold is not None:
                if not isinstance(threshold, int) or threshold < 0 or threshold > 255:
                    msg = f"[LINTER ERROR] opaque_mask.threshold 越界：必須是 [0, 255] 之間的整數，得到 '{threshold}'。"
                    cov_params_meta = _meta.get("coverage_params", {})
                    op_meta = cov_params_meta.get("opaque_mask", {})
                    if code and "threshold" in op_meta:
                        line, col = op_meta["threshold"]
                        msg = format_error_trace(code, line, col, msg)
                    elif code and "coverage" in _meta:
                        line, col = _meta["coverage"]
                        msg = format_error_trace(code, line, col, msg)
                    raise ValueError(msg)
                    
    return True

def inspect_layerspec_file(input_path):
    """校驗單一 .layerspec 檔案"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到輸入的圖層 DSL 檔案: {input_path}")
        
    with open(input_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    ast = parse_layer_code(code)
    inspect_layer_manifest_ast(ast, code=code)
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LayerSpec DSL 靜態語意校驗器 CLI")
    parser.add_argument("-i", "--input", help="輸入的 .layerspec 檔案路徑", required=True)
    
    args = parser.parse_args()
    
    try:
        inspect_layerspec_file(args.input)
        print(f"[+] 靜態語意校驗成功！檔案 [{args.input}] 完全符合 Ingestion 預檢規範。")
        sys.exit(0)
    except Exception as e:
        print(f"[X] 靜態校驗失敗:\n{e}")
        sys.exit(1)
