#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_compiler.py
功能：對 SkinSpec Island 編譯器進行全方位的單元與端到端自動化測試。
測試項：
1. 合法契約語法糖編譯：比對 compile 產出與期望 expected.json 是否 100% 結構一致。
2. 語法錯誤 (SyntaxError) 捕獲：缺失大括弧、非預期 token、不合規參數等。
3. 零動態執行漏洞 (Security Sandboxing)：驗證輸入惡意 exec/eval 代碼會被安全攔截，只會被視為語法錯誤，不會被執行。
"""

import os
import sys
import unittest
import json
import tempfile
import numpy as np

# 設定導入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(current_dir, "..", "islands")))
sys.path.append(os.path.abspath(os.path.join(current_dir, "..", "islands", "skin_spec", "reference_python")))
sys.path.append(os.path.abspath(os.path.join(current_dir, "..", "islands", "layer_spec", "reference_python")))

from parse_skin_spec import parse_code
from compile_skin_spec import compile_ast_to_manifest
from validate_output import validate_generated_manifest
from inspect_skin_spec import inspect_manifest_ast

from parse_layer_spec import parse_layer_code
from compile_layer_spec import compile_ast_to_layerspec_json
from inspect_layer_spec import inspect_layer_manifest_ast
from compile_all import compile_all_assets

class TestSkinSpecCompiler(unittest.TestCase):

    def setUp(self):
        self.valid_dsl = """
        skin terrain terrain_synthetic_v0.2.2 {
          schema rrkal.renderer_skin_asset.v0.2.2
          source SYNTHETIC_GENERATOR_V2
          projection EPSG:4326
          grid south_to_north west_to_east
          bounds lat -90 90 lon -180 180
          encoding int16_meter {
            scale 0.5
            offset 0.0
            nodata -32768
          }
          level 0 {
            elevation payloads/elevation_l0_i16.npz
            shape 180 360
            cell_size_deg 1.0
            valid_mask payloads/coverage/valid_elevation_mask_l0_u8.npz
            land_fraction payloads/coverage/land_fraction_l0_u8.npz
            water_fraction payloads/coverage/water_fraction_l0_u8.npz
            minmax payloads/minmax_l0_i16.npz scope global_lod_summary
          }
        }
        """

    def test_valid_compilation(self):
        """測試合法語法編譯並進行深度欄位比對"""
        ast = parse_code(self.valid_dsl)
        manifest = compile_ast_to_manifest(ast)
        
        self.assertEqual(manifest["schema"], "rrkal.renderer_skin_asset.v0.2.2")
        self.assertEqual(manifest["kind"], "terrain")
        self.assertEqual(manifest["asset_id"], "terrain_synthetic_v0.2.2")
        self.assertEqual(manifest["source_dataset"], "SYNTHETIC_GENERATOR_V2")
        self.assertEqual(manifest["encoding"]["scale"], 0.5)
        self.assertEqual(manifest["encoding"]["nodata_value"], -32768)
        self.assertEqual(manifest["grid"]["row_order"], "south_to_north")
        self.assertEqual(manifest["bounds"]["lat_max"], 90.0)
        
        # 驗證 levels 中自動推導之 raw_nbytes： 180 * 360 * 2 = 129600
        lvl0 = manifest["levels"][0]
        self.assertEqual(lvl0["level"], 0)
        self.assertEqual(lvl0["raw_nbytes"], 129600)
        self.assertEqual(lvl0["minmax_scope"], "global_lod_summary")
        
        # 驗證 checksums 註冊
        self.assertIn("payloads/elevation_l0_i16.npz", manifest["checksums"])

    def test_syntax_errors(self):
        """測試各種語法錯誤是否能被精準捕捉"""
        # 1. 缺失大括弧
        bad_dsl_1 = "skin terrain test_asset"
        with self.assertRaises(SyntaxError):
            parse_code(bad_dsl_1)
            
        # 2. 未知關鍵字
        bad_dsl_2 = """
        skin terrain test_asset {
          unknown_key abc
        }
        """
        with self.assertRaises(SyntaxError):
            parse_code(bad_dsl_2)
            
        # 3. 類型不符（如 shape 後面預期是數字，卻給了字串）
        bad_dsl_3 = """
        skin terrain test_asset {
          level 0 {
            shape abc def
          }
        }
        """
        with self.assertRaises(SyntaxError):
            parse_code(bad_dsl_3)

    def test_security_sandboxing(self):
        """測試零動態執行漏洞：注入 exec/eval 代碼會被安全攔截，決不被執行"""
        # 我們企圖在 identifier 處注入 python 腳本
        malicious_dsl = """
        skin terrain malicious {
          schema rrkal.renderer_skin_asset.v0.2.2
          source __import__('os').system('echo HACKED')
        }
        """
        with self.assertRaises(SyntaxError):
            parse_code(malicious_dsl)

    def test_sandbox_e2e_ingestion_interlock(self):
        """實裝沙盒二進位聯鎖 E2E 測試：動態建立臨時 npz 實體，編譯指紋感知 manifest，引導主線校驗器通關"""
        # 1. 建立臨時沙盒 vizasset 目錄
        with tempfile.TemporaryDirectory() as tmp_dir:
            skin_root = os.path.join(tmp_dir, "skins", "terrain")
            os.makedirs(skin_root, exist_ok=True)
            
            # 建立 Ingestion asset.json 容器
            asset_json = {
                "required_skins": {
                    "terrain": "skins/terrain/manifest.json"
                }
            }
            with open(os.path.join(tmp_dir, "asset.json"), "w", encoding="utf-8") as f:
                json.dump(asset_json, f, indent=2)
                
            # 2. 動態生成 level 0 所需的 5 個實體模擬 .npz 檔案，精確大小與 shape 一致
            h, w = 180, 360
            
            # A. elevation_l0_i16.npz (int16, 2D)
            elev_data = np.zeros((h, w), dtype=np.int16)
            elev_path = os.path.join(skin_root, "payloads", "elevation_l0_i16.npz")
            os.makedirs(os.path.dirname(elev_path), exist_ok=True)
            np.savez_compressed(elev_path, data=elev_data)
            
            # B. valid_mask_l0_u8.npz (uint8, 2D)
            mask_data = np.ones((h, w), dtype=np.uint8)
            mask_path = os.path.join(skin_root, "payloads", "coverage", "valid_elevation_mask_l0_u8.npz")
            os.makedirs(os.path.dirname(mask_path), exist_ok=True)
            np.savez_compressed(mask_path, data=mask_data)
            
            # C. land_fraction_l0_u8.npz (uint8, 2D)
            land_path = os.path.join(skin_root, "payloads", "coverage", "land_fraction_l0_u8.npz")
            np.savez_compressed(land_path, data=mask_data)
            
            # D. water_fraction_l0_u8.npz (uint8, 2D)
            water_path = os.path.join(skin_root, "payloads", "coverage", "water_fraction_l0_u8.npz")
            np.savez_compressed(water_path, data=mask_data)
            
            # E. minmax_l0_i16.npz (int16, 1D, shape=(1,))
            minmax_data = np.array([0], dtype=np.int16)
            minmax_path = os.path.join(skin_root, "payloads", "minmax_l0_i16.npz")
            os.makedirs(os.path.dirname(minmax_path), exist_ok=True)
            np.savez_compressed(minmax_path, min=minmax_data, max=minmax_data)
            
            # 3. 呼叫指紋感知編譯器編譯 valid_dsl，傳入 asset_root=skin_root
            ast = parse_code(self.valid_dsl)
            manifest = compile_ast_to_manifest(ast, asset_root=skin_root)
            
            # 寫入 skins/terrain/manifest.json
            manifest_json_path = os.path.join(skin_root, "manifest.json")
            with open(manifest_json_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                
            # 4. 安全引導主線驗證器對此沙盒 asset 進行 ingestion 校驗
            # 自動偵測本機 vis_2_dis 目錄
            vis_2_dis_root = os.path.abspath(os.path.join(current_dir, "..", "..", "vis_2_dis"))
            
            # 觸發聯鎖驗證
            is_valid = validate_generated_manifest(manifest_json_path, vis_2_dis_root=vis_2_dis_root)
            self.assertTrue(is_valid)

    def test_multi_level_pyramid_ingestion_interlock(self):
        """實裝多層級金字塔 E2E 測試：動態建立 LOD 0 與 LOD 1 實體 npz，編譯指紋感知 manifest，引導主線驗證"""
        multi_level_dsl = """
        skin terrain terrain_synthetic_pyramid {
          schema rrkal.renderer_skin_asset.v0.2.2
          source SYNTHETIC_GENERATOR_V2
          projection EPSG:4326
          grid south_to_north west_to_east
          bounds lat -90 90 lon -180 180
          encoding int16_meter {
            scale 0.5
            offset 0.0
            nodata -32768
          }
          level 0 {
            elevation payloads/elevation_l0_i16.npz
            shape 180 360
            cell_size_deg 1.0
            valid_mask payloads/coverage/valid_elevation_mask_l0_u8.npz
            land_fraction payloads/coverage/land_fraction_l0_u8.npz
            water_fraction payloads/coverage/water_fraction_l0_u8.npz
            minmax payloads/minmax_l0_i16.npz scope global_lod_summary
          }
          level 1 {
            elevation payloads/elevation_l1_i16.npz
            shape 90 180
            cell_size_deg 2.0
            valid_mask payloads/coverage/valid_elevation_mask_l1_u8.npz
            land_fraction payloads/coverage/land_fraction_l1_u8.npz
            water_fraction payloads/coverage/water_fraction_l1_u8.npz
            minmax payloads/minmax_l1_i16.npz scope global_lod_summary
          }
        }
        """
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            skin_root = os.path.join(tmp_dir, "skins", "terrain")
            os.makedirs(skin_root, exist_ok=True)
            
            # 建立 Ingestion asset.json 容器
            asset_json = {
                "required_skins": {
                    "terrain": "skins/terrain/manifest.json"
                }
            }
            with open(os.path.join(tmp_dir, "asset.json"), "w", encoding="utf-8") as f:
                json.dump(asset_json, f, indent=2)
                
            # 2. 動態生成雙層級 (LOD 0 和 LOD 1) 所有的實體模擬 .npz 檔案
            h_l0, w_l0 = 180, 360
            h_l1, w_l1 = 90, 180
            
            # 輔助函式：動態生成符合 Ingestion 約定的 npz 檔案
            def make_lvl_npz(h, w, lvl_num):
                # elev (int16, 2D)
                elev_path = os.path.join(skin_root, "payloads", f"elevation_l{lvl_num}_i16.npz")
                os.makedirs(os.path.dirname(elev_path), exist_ok=True)
                np.savez_compressed(elev_path, data=np.zeros((h, w), dtype=np.int16))
                
                # mask, land, water (uint8, 2D)
                mask_data = np.ones((h, w), dtype=np.uint8)
                for name in ["valid_elevation_mask", "land_fraction", "water_fraction"]:
                    path = os.path.join(skin_root, "payloads", "coverage", f"{name}_l{lvl_num}_u8.npz")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    np.savez_compressed(path, data=mask_data)
                    
                # minmax (int16, 1D, shape=(1,))
                minmax_path = os.path.join(skin_root, "payloads", f"minmax_l{lvl_num}_i16.npz")
                os.makedirs(os.path.dirname(minmax_path), exist_ok=True)
                np.savez_compressed(minmax_path, min=np.array([0], dtype=np.int16), max=np.array([0], dtype=np.int16))
                
            # 生成 LOD 0 和 LOD 1
            make_lvl_npz(h_l0, w_l0, 0)
            make_lvl_npz(h_l1, w_l1, 1)
            
            # 3. 呼叫指紋與大小感知編譯器，進行雙層級編譯
            ast = parse_code(multi_level_dsl)
            manifest = compile_ast_to_manifest(ast, asset_root=skin_root)
            
            # 驗證產出 manifest 是否精確回填了兩個層級的實體檔案屬性
            self.assertEqual(len(manifest["levels"]), 2)
            self.assertEqual(manifest["levels"][0]["raw_nbytes"], h_l0 * w_l0 * 2)
            self.assertEqual(manifest["levels"][1]["raw_nbytes"], h_l1 * w_l1 * 2)
            
            # 驗證 checksums 指紋
            self.assertIn("payloads/elevation_l0_i16.npz", manifest["checksums"])
            self.assertIn("payloads/elevation_l1_i16.npz", manifest["checksums"])
            
            # 寫入 skins/terrain/manifest.json
            manifest_json_path = os.path.join(skin_root, "manifest.json")
            with open(manifest_json_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                
            # 4. 安全引導主線驗證器對此雙層級沙盒資產進行 ingestion 驗證
            vis_2_dis_root = os.path.abspath(os.path.join(current_dir, "..", "..", "vis_2_dis"))
            is_valid = validate_generated_manifest(manifest_json_path, vis_2_dis_root=vis_2_dis_root)
            self.assertTrue(is_valid)

    def test_linter_diagnostics(self):
        """測試 Linter 預檢校驗器：覆蓋 bounds 越界、scale 負數、LOD 不連續、shape 零值等所有 Ingestion 預檢規則"""
        # 1. 驗證合規 DSL 能順利通關
        ast_valid = parse_code(self.valid_dsl)
        self.assertTrue(inspect_manifest_ast(ast_valid))

        # 2. 驗證緯度 bounds 越界攔截
        bad_dsl_lat = self.valid_dsl.replace("bounds lat -90 90", "bounds lat -120 90")
        with self.assertRaises(ValueError):
            inspect_manifest_ast(parse_code(bad_dsl_lat))

        # 3. 驗證經度 bounds 越界與順序反向攔截
        bad_dsl_lon = self.valid_dsl.replace("bounds lat -90 90 lon -180 180", "bounds lat -90 90 lon 180 -180")
        with self.assertRaises(ValueError):
            inspect_manifest_ast(parse_code(bad_dsl_lon))

        # 4. 驗證 encoding scale 負值攔截
        bad_dsl_scale = self.valid_dsl.replace("scale 0.5", "scale -0.5")
        with self.assertRaises(ValueError):
            inspect_manifest_ast(parse_code(bad_dsl_scale))

        # 5. 驗證 levels 金字塔層級不連續性攔截 (缺少 level 0)
        bad_dsl_lod_jump = self.valid_dsl.replace("level 0 {", "level 1 {")
        with self.assertRaises(ValueError):
            inspect_manifest_ast(parse_code(bad_dsl_lod_jump))

        # 6. 驗證 LOD 網格尺寸 shape 零值非法性攔截
        bad_dsl_shape = self.valid_dsl.replace("shape 180 360", "shape 0 360")
        with self.assertRaises(ValueError):
            inspect_manifest_ast(parse_code(bad_dsl_shape))

        # 7. 驗證 schema 版本非法性攔截
        bad_dsl_schema = self.valid_dsl.replace("schema rrkal.renderer_skin_asset.v0.2.2", "schema rrkal.renderer_skin_asset.v9.9.9")
        with self.assertRaises(ValueError):
            inspect_manifest_ast(parse_code(bad_dsl_schema))

    def test_layer_spec_parser_and_compiler(self):
        """測試正常圖層 DSL 規格的解析與編譯"""
        layer_dsl = """
        layer terrain_composite {
          schema rrkal_displaytools.render_layer_spec.v0.2.1
          layer_id synthetic_terrain_layer
          layer_type terrain_skin
          source_skin_asset terrain_synthetic_v0.2.2
          source_manifest skins/terrain/manifest.json
          visible true
          opacity 0.85
          blend_mode overlay
          render_queue_group opaque_terrain
          lod_policy {
            mode auto
            interactive_level 2
            preview_level 1
            quality_level 0
            export_level 0
          }
          coverage {
            coverage_mask_kind valid_elevation_mask
            resolve_by_lod true
            opaque_mask {
              opaque_mask_kind terrain_opaque_mask
              threshold 255
            }
            requires_underlay false
          }
          update_policy {
            interactive cached
            settled refresh_if_dirty
            export require_ready
          }
          status ready
        }
        """
        ast = parse_layer_code(layer_dsl)
        self.assertEqual(ast["layer_name"], "terrain_composite")
        self.assertEqual(ast["schema"], "rrkal_displaytools.render_layer_spec.v0.2.1")
        self.assertEqual(ast["opacity"], 0.85)
        self.assertEqual(ast["visible"], True)
        self.assertEqual(ast["blend_mode"], "overlay")
        
        # 驗證編譯輸出
        compiled = compile_ast_to_layerspec_json(ast)
        self.assertEqual(compiled["schema"], "rrkal_displaytools.render_layer_spec.v0.2.1")
        self.assertEqual(compiled["opacity"], 0.85)
        self.assertEqual(compiled["blend_mode"], "overlay")
        self.assertEqual(compiled["lod_policy"]["interactive_level"], 2)
        self.assertEqual(compiled["coverage"]["opaque_mask"]["threshold"], 255)

    def test_layer_spec_linter_diagnostics(self):
        """測試圖層 Linter 預檢規則對各種越界與缺陷圖層 DSL 的攔截"""
        valid_layer_dsl = """
        layer test_layer {
          schema rrkal_displaytools.render_layer_spec.v0.2.1
          layer_id test_id
          opacity 1.0
          blend_mode normal
        }
        """
        # 1. 合規 DSL 順利通過
        self.assertTrue(inspect_layer_manifest_ast(parse_layer_code(valid_layer_dsl)))
        
        # 2. opacity 越界攔截 (> 1.0)
        bad_dsl_opacity = valid_layer_dsl.replace("opacity 1.0", "opacity 1.5")
        with self.assertRaises(ValueError):
            inspect_layer_manifest_ast(parse_layer_code(bad_dsl_opacity))
            
        # 3. opacity 負值越界攔截
        bad_dsl_neg_opacity = valid_layer_dsl.replace("opacity 1.0", "opacity -0.1")
        with self.assertRaises(ValueError):
            inspect_layer_manifest_ast(parse_layer_code(bad_dsl_neg_opacity))
            
        # 4. 未知 blend_mode 攔截
        bad_dsl_blend = valid_layer_dsl.replace("blend_mode normal", "blend_mode alpha_blend_extreme")
        with self.assertRaises(ValueError):
            inspect_layer_manifest_ast(parse_layer_code(bad_dsl_blend))
            
        # 5. schema 錯誤攔截
        bad_dsl_schema = valid_layer_dsl.replace("schema rrkal_displaytools.render_layer_spec.v0.2.1", "schema rrkal_displaytools.render_layer_spec.v9.9.9")
        with self.assertRaises(ValueError):
            inspect_layer_manifest_ast(parse_layer_code(bad_dsl_schema))
            
        # 6. threshold 越界攔截
        bad_dsl_threshold = """
        layer test_layer {
          schema rrkal_displaytools.render_layer_spec.v0.2.1
          layer_id test_id
          coverage {
            opaque_mask {
              threshold 300
            }
          }
        }
        """
        with self.assertRaises(ValueError):
            inspect_layer_manifest_ast(parse_layer_code(bad_dsl_threshold))

    def test_orchestrator_global_compilation(self):
        """測試全域 Orchestrator 大包編譯與發佈"""
        with tempfile.TemporaryDirectory() as tmp_in_dir:
            with tempfile.TemporaryDirectory() as tmp_out_dir:
                # 建立合規的 .skinisland 皮層契約
                with open(os.path.join(tmp_in_dir, "terrain.skinisland"), "w", encoding="utf-8") as f:
                    f.write(self.valid_dsl)
                    
                # 建立關聯的 .layerspec 圖層規格 (source_skin_asset 對位對齊)
                layer_spec_dsl = """
                layer terrain_composite {
                  schema rrkal_displaytools.render_layer_spec.v0.2.1
                  layer_id synthetic_terrain_layer
                  source_skin_asset terrain_synthetic_v0.2.2
                  source_manifest skins/terrain/manifest.json
                  blend_mode normal
                }
                """
                with open(os.path.join(tmp_in_dir, "terrain.layerspec"), "w", encoding="utf-8") as f:
                    f.write(layer_spec_dsl)
                    
                # 觸發全域大包編譯
                skins_manifests, layers_compiled = compile_all_assets(tmp_in_dir, tmp_out_dir)
                
                self.assertIn("terrain_synthetic_v0.2.2", skins_manifests)
                self.assertEqual(len(layers_compiled), 1)
                self.assertEqual(layers_compiled[0]["source_skin_asset"], "terrain_synthetic_v0.2.2")
                
                # 驗證實體 JSON 是否正確生成
                self.assertTrue(os.path.exists(os.path.join(tmp_out_dir, "skins", "terrain", "manifest.json")))
                self.assertTrue(os.path.exists(os.path.join(tmp_out_dir, "render_layer_spec.json")))

    def test_orchestrator_cross_validation_fail(self):
        """測試 Orchestrator 的交叉安全校驗：攔截未對齊的無效皮層資產引用，提前阻斷"""
        with tempfile.TemporaryDirectory() as tmp_in_dir:
            with tempfile.TemporaryDirectory() as tmp_out_dir:
                # 1. 建立皮層契約，其資產 ID 為 'terrain_synthetic_v0.2.2'
                with open(os.path.join(tmp_in_dir, "terrain.skinisland"), "w", encoding="utf-8") as f:
                    f.write(self.valid_dsl)
                    
                # 2. 建立圖層規格，但參考了不存在的 'terrain_hacked_asset_v999'
                malicious_layer_dsl = """
                layer terrain_composite {
                  schema rrkal_displaytools.render_layer_spec.v0.2.1
                  layer_id synthetic_terrain_layer
                  source_skin_asset terrain_hacked_asset_v999
                  source_manifest skins/terrain/manifest.json
                  blend_mode normal
                }
                """
                with open(os.path.join(tmp_in_dir, "terrain.layerspec"), "w", encoding="utf-8") as f:
                    f.write(malicious_layer_dsl)
                    
                # 斷言交叉語意校驗能正確拋出 ValueError，並安全阻斷編譯
                with self.assertRaises(ValueError) as ctx:
                    compile_all_assets(tmp_in_dir, tmp_out_dir)
                self.assertIn("CROSS-VALIDATION ERROR", str(ctx.exception))

    def test_column_level_syntax_error_trace(self):
        """測試極限精密化：列級語法診斷 Caret Trace 錯誤回溯"""
        # 構造 bounds 緯度越界的非法 DSL
        bad_dsl = """
        skin terrain terrain_synthetic_v0.2.2 {
          schema rrkal.renderer_skin_asset.v0.2.2
          bounds lat -120 90 lon -180 180
        }
        """
        # 斷言 inspect_manifest_ast 拋出 ValueError
        with self.assertRaises(ValueError) as ctx:
            inspect_manifest_ast(parse_code(bad_dsl), code=bad_dsl)
        
        # 驗證錯誤訊息中精確包含 Caret '^' 箭頭指向以及正確的錯誤位置
        err_msg = str(ctx.exception)
        self.assertIn("bounds lat -120 90 lon -180 180", err_msg)
        self.assertIn("^", err_msg)
        self.assertIn("在第 4 行，位置 11", err_msg)

    def test_fidelity_metrics_and_review_json(self):
        """測試極限精密化：逐像素量化還原 RMSE 與 MAE 演算，並驗證自動發佈 review.json"""
        h, w = 180, 360
        # 1. 模擬高精度原始浮點數據（全平原 100.2m 地形）
        raw_float = np.ones((h, w), dtype=np.float64) * 100.2
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            skin_root = os.path.join(tmp_dir, "skins", "terrain")
            os.makedirs(skin_root, exist_ok=True)
            
            # 2. 模擬 Ingestion 二進位實體，高程全部量化為 200 (量化還原：200 * 0.5 + 0.0 = 100.0)
            # MAE 應為 |100.0 - 100.2| = 0.2
            elev_data = np.ones((h, w), dtype=np.int16) * 200
            elev_path = os.path.join(skin_root, "payloads", "elevation_l0_i16.npz")
            os.makedirs(os.path.dirname(elev_path), exist_ok=True)
            np.savez_compressed(elev_path, data=elev_data)
            
            # 建立其餘必要的模擬覆蓋率與 MinMax 以便通過 file checks
            mask_data = np.ones((h, w), dtype=np.uint8)
            os.makedirs(os.path.join(skin_root, "payloads", "coverage"), exist_ok=True)
            np.savez_compressed(os.path.join(skin_root, "payloads", "coverage", "valid_elevation_mask_l0_u8.npz"), data=mask_data)
            np.savez_compressed(os.path.join(skin_root, "payloads", "coverage", "land_fraction_l0_u8.npz"), data=mask_data)
            np.savez_compressed(os.path.join(skin_root, "payloads", "coverage", "water_fraction_l0_u8.npz"), data=mask_data)
            np.savez_compressed(os.path.join(skin_root, "payloads", "minmax_l0_i16.npz"), min=np.array([0]), max=np.array([0]))
            
            # 3. 編譯
            ast = parse_code(self.valid_dsl)
            manifest = compile_ast_to_manifest(ast, asset_root=skin_root, raw_float_grid=raw_float)
            
            # 4. 斷言 review.json 是否在臨時容器根目錄（tmp_dir）下順利發佈並產出
            review_path = os.path.join(tmp_dir, "review.json")
            self.assertTrue(os.path.exists(review_path))
            
            with open(review_path, "r", encoding="utf-8") as f:
                review = json.load(f)
                
            self.assertEqual(review["schema"], "rrkal.renderer_skin_asset.review.v0.2.2")
            metrics = review["fidelity_metrics"]
            # 誤差應精確為 0.2
            self.assertAlmostEqual(metrics["rmse"], 0.2, places=4)
            self.assertAlmostEqual(metrics["mae"], 0.2, places=4)
            self.assertAlmostEqual(metrics["max_absolute_error"], 0.2, places=4)

if __name__ == "__main__":
    unittest.main()
