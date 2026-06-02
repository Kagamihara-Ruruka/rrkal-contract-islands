#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compile_all.py
功能: 全域契約大包編譯整合器 (Orchestrator)。
極限精密化: 整合列級診斷 Caret Trace 錯誤回溯，並於交叉語意校驗失敗時精確指出出錯的 DSL 原始行與位置。
"""

import os
import sys
import json
import argparse

# 設定相對導入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(current_dir, "skin_spec", "reference_python")))
sys.path.append(os.path.abspath(os.path.join(current_dir, "layer_spec", "reference_python")))

try:
    from parse_skin_spec import parse_code as parse_skin, format_error_trace
    from compile_skin_spec import compile_ast_to_manifest as compile_skin_ast
    from inspect_skin_spec import inspect_manifest_ast as inspect_skin_ast
    
    from parse_layer_spec import parse_layer_code as parse_layer
    from compile_layer_spec import compile_ast_to_layerspec_json as compile_layer_ast
    from inspect_layer_spec import inspect_layer_manifest_ast as inspect_layer_ast
except ImportError as e:
    print(f"[X] 內部導入失敗，請確認 reference_python 目錄結構是否完好: {e}")
    sys.exit(1)

def scan_files(root_dir, extension):
    """遞迴掃描特定副檔名的檔案"""
    found = []
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith(extension):
                found.append(os.path.join(root, f))
    return found

def compile_all_assets(input_dir, output_dir, asset_root=None, raw_float_grid=None):
    """進行全域契約掃描、列級 Linter 校驗、交叉檢查與發佈大包"""
    print(f"[*] 開始對目錄 [{input_dir}] 進行全域契約大包編譯...")
    
    # 1. 掃描所有契約原始檔
    skin_files = scan_files(input_dir, ".skinisland")
    layer_files = scan_files(input_dir, ".layerspec")
    
    print(f"    --> 偵測到 {len(skin_files)} 個皮層契約 (.skinisland)")
    print(f"    --> 偵測到 {len(layer_files)} 個圖層規格 (.layerspec)")
    
    # 2. 解析並校驗所有 .skinisland (皮層契約)
    skins_manifests = {} # asset_id -> manifest
    skins_ast = {}
    
    for sf in skin_files:
        print(f"[*] 正在解析與校驗皮層契約: {os.path.basename(sf)}")
        with open(sf, "r", encoding="utf-8") as f:
            code = f.read()
        try:
            ast = parse_skin(code)
            # 注入原始 code 供後續分析
            ast["_code"] = code
            
            # 進行極限精密化的列級 Linter 預檢
            inspect_skin_ast(ast, code=code)
            
            # 編譯皮層，可傳入 raw_float_grid 用於極限精密化保真度計算
            manifest = compile_skin_ast(ast, asset_root=asset_root, raw_float_grid=raw_float_grid)
            asset_id = manifest.get("asset_id")
            
            skins_manifests[asset_id] = manifest
            skins_ast[asset_id] = ast
        except Exception as e:
            raise ValueError(f"皮層契約 [{sf}] 編譯/校驗失敗:\n{e}")
            
    # 3. 解析並校驗所有 .layerspec (圖層規格)
    layers_compiled = []
    layers_ast = []
    
    for lf in layer_files:
        print(f"[*] 正在解析與校驗圖層規格: {os.path.basename(lf)}")
        with open(lf, "r", encoding="utf-8") as f:
            code = f.read()
        try:
            ast = parse_layer(code)
            ast["_code"] = code
            
            # 進行極限精密化的列級 Linter 預檢
            inspect_layer_ast(ast, code=code)
            
            # 編譯圖層 spec
            spec = compile_layer_ast(ast)
            
            layers_compiled.append(spec)
            layers_ast.append(ast)
        except Exception as e:
            raise ValueError(f"圖層規格 [{lf}] 編譯/校驗失敗:\n{e}")
            
    # 4. 進行交叉語意校驗 (Cross-validation) 並整合 Caret Trace
    print("[*] 正在進行跨契約交叉語意安全校驗 (Cross-validation)...")
    for idx, spec in enumerate(layers_compiled):
        source_skin = spec.get("source_skin_asset")
        if source_skin not in skins_manifests:
            msg = (
                f"[CROSS-VALIDATION ERROR] 安全漏洞攔截：\n"
                f"圖層規格 '{spec.get('layer_id')}' 聲明參考了皮層資產 '{source_skin}'，\n"
                f"但在當前編譯上下文中未找到任何對應的 '.skinisland' 宣告！"
            )
            ast_layer = layers_ast[idx]
            # 提取 _meta 中的列號，拋出極限精密化錯誤回溯
            if "_meta" in ast_layer and "source_skin_asset" in ast_layer["_meta"]:
                layer_code = ast_layer.get("_code")
                line, col = ast_layer["_meta"]["source_skin_asset"]
                msg = format_error_trace(layer_code, line, col, msg)
            raise ValueError(msg)
            
    print("[+] 交叉語意安全校驗成功！所有圖層與皮層契約完美對齊。")
    
    # 5. 寫入輸出發佈目錄
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
        # 寫入皮層 (Skins)
        for asset_id, manifest in skins_manifests.items():
            kind = manifest.get("kind", "terrain")
            skin_path = os.path.join(output_dir, "skins", kind, "manifest.json")
            os.makedirs(os.path.dirname(skin_path), exist_ok=True)
            with open(skin_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            print(f"    --> 已寫入皮層 Manifest: {skin_path}")
            
        # 寫入圖層規格 (Layers)
        for spec in layers_compiled:
            layer_path = os.path.join(output_dir, "render_layer_spec.json")
            with open(layer_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            print(f"    --> 已寫入圖層 Spec: {layer_path}")
            
        print(f"[+] 全域契約大包發佈完成！目錄位置: {output_dir}")
        
    return skins_manifests, layers_compiled

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="語言島全域大包編譯整合器 CLI")
    parser.add_argument("-i", "--input", help="要掃描契約的專案輸入目錄", required=True)
    parser.add_argument("-o", "--output", help="編譯 JSON 發佈的輸出目錄", required=True)
    parser.add_argument("-a", "--asset-root", help="皮層 NPZ 二進位實體所在的 asset_root 目錄 (選填)", required=False)
    
    args = parser.parse_args()
    
    try:
        compile_all_assets(args.input, args.output, args.asset_root)
        sys.exit(0)
    except Exception as e:
        print(f"[X] 全域大包編譯失敗:\n{e}")
        sys.exit(1)
