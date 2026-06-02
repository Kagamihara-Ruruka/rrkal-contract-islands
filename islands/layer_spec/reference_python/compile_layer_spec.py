#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compile_layer_spec.py
功能：將 LayerSpec DSL AST 編譯為與 displaytools 100% 相容的 JSON 屬性配置檔。
"""

import os
import json
import sys
from parse_layer_spec import parse_layer_code

def compile_ast_to_layerspec_json(ast):
    """將語意解析後的 AST 轉化並規範化為標準 JSON 結構"""
    # 建立基礎結構，並設定預設值以防漏失
    compiled = {
        "schema": ast.get("schema", "rrkal_displaytools.render_layer_spec.v0.2.1"),
        "layer_id": ast.get("layer_id", "unnamed_layer"),
        "layer_type": ast.get("layer_type", "terrain_skin"),
        "source_skin_asset": ast.get("source_skin_asset", ""),
        "source_manifest": ast.get("source_manifest", ""),
        "visible": ast.get("visible", True),
        "opacity": float(ast.get("opacity", 1.0)),
        # 強制轉換成小寫以與 displaytools 運行時完全對齊
        "blend_mode": ast.get("blend_mode", "normal").lower(),
        "render_queue_group": ast.get("render_queue_group", "opaque_terrain"),
    }
    
    # 填入 lod_policy
    ast_lod = ast.get("lod_policy", {})
    compiled["lod_policy"] = {
        "mode": ast_lod.get("mode", "auto"),
        "interactive_level": int(ast_lod.get("interactive_level", 2)),
        "preview_level": int(ast_lod.get("preview_level", 1)),
        "quality_level": int(ast_lod.get("quality_level", 0)),
        "export_level": int(ast_lod.get("export_level", 0))
    }
    
    # 填入 coverage
    ast_cov = ast.get("coverage", {})
    coverage = {
        "coverage_mask_kind": ast_cov.get("coverage_mask_kind", "valid_elevation_mask"),
        "resolve_by_lod": ast_cov.get("resolve_by_lod", True),
        "requires_underlay": ast_cov.get("requires_underlay", False)
    }
    
    # 嵌套的 opaque_mask
    ast_op = ast_cov.get("opaque_mask", {})
    if ast_op:
        coverage["opaque_mask"] = {
            "opaque_mask_kind": ast_op.get("opaque_mask_kind", "terrain_opaque_mask"),
            "threshold": int(ast_op.get("threshold", 255))
        }
    compiled["coverage"] = coverage
    
    # 填入 update_policy
    ast_up = ast.get("update_policy", {})
    compiled["update_policy"] = {
        "interactive": ast_up.get("interactive", "cached"),
        "settled": ast_up.get("settled", "refresh_if_dirty"),
        "export": ast_up.get("export", "require_ready")
    }
    
    # 狀態
    compiled["status"] = ast.get("status", "ready")
    
    return compiled

def compile_layerspec_file(input_path, output_path=None):
    """讀取並編譯指定的 .layerspec 檔案"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到輸入的圖層 DSL 檔案: {input_path}")
        
    with open(input_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    ast = parse_layer_code(code)
    compiled = compile_ast_to_layerspec_json(ast)
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(compiled, f, indent=2, ensure_ascii=False)
        print(f"[+] 編譯成功！已導出 RenderLayerSpec 配置至: {output_path}")
    else:
        print(json.dumps(compiled, indent=2, ensure_ascii=False))
        
    return compiled

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LayerSpec DSL 編譯器 CLI")
    parser.add_argument("-i", "--input", help="輸入的 .layerspec DSL 檔案路徑", required=False)
    parser.add_argument("-o", "--output", help="輸出的 .json 配置檔案路徑", required=False)
    
    args = parser.parse_args()
    
    if args.input:
        try:
            compile_layerspec_file(args.input, args.output)
        except Exception as e:
            print(f"[X] 編譯失敗: {e}")
            sys.exit(1)
    else:
        # 進行輕量化本地測試
        current_dir = os.path.dirname(os.path.abspath(__file__))
        example_path = os.path.abspath(os.path.join(current_dir, "..", "examples", "synthetic_terrain.layerspec"))
        if os.path.exists(example_path):
            print(f"[*] 執行範例檔案自檢編譯: {example_path}")
            compile_layerspec_file(example_path)
        else:
            print("[*] 找不到範例檔案，略過自檢。")
