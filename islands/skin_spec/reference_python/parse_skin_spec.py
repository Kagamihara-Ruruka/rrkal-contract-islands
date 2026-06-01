#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_skin_spec.py
功能：手寫 SkinSpec Island DSL 的 Tokenizer 與遞迴下降語法解析器。
特點：
1. 零第三方庫依賴 (zero-dependency)。
2. 100% 物理杜絕 eval/exec/__import__ 等動態指令執行漏洞，只做純文字處理與 AST 構建。
"""

import re
import sys

# 詞法定義規則，精確過濾不合法字元
TOKEN_SPEC = [
    ('COMMENT',    r'#.*'),
    ('LBRACE',     r'\{'),
    ('RBRACE',     r'\}'),
    ('NUMBER',     r'-?\d+(?:\.\d+)?'),
    # 限制 STRING 必須至少包含一個斜線、點號或破折號，以與純單字區分，並置於最前以最長匹配
    ('STRING',     r'[a-zA-Z0-9_\-\./]*[\./\-][a-zA-Z0-9_\-\./]*'),
    ('KEYWORD',    r'\b(?:skin|schema|source|projection|grid|bounds|encoding|level|scale|offset|nodata|elevation|shape|cell_size_deg|valid_mask|land_fraction|water_fraction|minmax|scope)\b'),
    ('IDENTIFIER', r'\b[a-zA-Z_][a-zA-Z0-9_\.:]*\b'),
    ('WS',         r'\s+'),
]

def tokenize(code):
    """安全詞法掃描器：切碎 Tokens，不調用 eval"""
    tokens = []
    lines = code.split('\n')
    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        pos = 0
        while pos < len(line):
            match = None
            for token_type, regex in TOKEN_SPEC:
                pattern = re.compile(regex)
                m = pattern.match(line, pos)
                if m:
                    match = m
                    text = m.group(0)
                    # 過濾空白與註解
                    if token_type != 'WS' and token_type != 'COMMENT':
                        tokens.append((token_type, text, line_num, pos + 1))
                    pos = m.end()
                    break
            if not match:
                raise SyntaxError(f"[LEXER ERROR] 發現非法字元 '{line[pos]}' 於第 {line_num} 行，位置 {pos + 1}")
    return tokens

class SkinSpecParser:
    """遞迴下降解析器 (Recursive Descent Parser)"""
    def __init__(self, tokens):
        self.tokens = tokens
        self.idx = 0

    def peek(self):
        """觀測當前 Token，不消耗"""
        if self.idx < len(self.tokens):
            return self.tokens[self.idx]
        return None

    def consume(self, expected_type=None, expected_val=None):
        """消耗並驗證當前 Token，支援 IDENTIFIER 與 STRING 互通容錯"""
        tok = self.peek()
        if not tok:
            raise SyntaxError("[PARSER ERROR] 語法錯誤：未預期的檔案結尾 (EOF)")
        tok_type, val, line, pos = tok
        
        # 實作 STRING 與 IDENTIFIER 的類型互通容錯
        is_type_match = False
        if expected_type:
            if tok_type == expected_type:
                is_type_match = True
            elif expected_type == 'STRING' and tok_type == 'IDENTIFIER':
                is_type_match = True
            elif expected_type == 'IDENTIFIER' and tok_type == 'STRING':
                is_type_match = True
        else:
            is_type_match = True
            
        if expected_type and not is_type_match:
            raise SyntaxError(f"[PARSER ERROR] 語法錯誤：預期 Token 型態為 {expected_type}，但得到 {tok_type} ('{val}') 於第 {line} 行，位置 {pos}")
        if expected_val and val != expected_val:
            raise SyntaxError(f"[PARSER ERROR] 語法錯誤：預期值為 '{expected_val}'，但得到 '{val}' 於第 {line} 行，位置 {pos}")
        self.idx += 1
        return tok

    def parse(self):
        """主解析入口"""
        # skin terrain terrain_synthetic_v0.2.2 {
        self.consume('KEYWORD', 'skin')
        kind_tok = self.consume('IDENTIFIER')
        id_tok = self.consume('IDENTIFIER')
        self.consume('LBRACE')
        
        ast = {
            "kind": kind_tok[1],
            "asset_id": id_tok[1],
            "levels": []
        }
        
        while self.peek() and self.peek()[0] != 'RBRACE':
            tok = self.peek()
            val = tok[1]
            if val == 'schema':
                self.consume('KEYWORD', 'schema')
                val_tok = self.consume('IDENTIFIER')
                ast["schema"] = val_tok[1]
            elif val == 'source':
                self.consume('KEYWORD', 'source')
                val_tok = self.consume('IDENTIFIER')
                ast["source_dataset"] = val_tok[1]
            elif val == 'projection':
                self.consume('KEYWORD', 'projection')
                val_tok = self.consume('IDENTIFIER')
                ast["projection"] = {"system": val_tok[1]}
            elif val == 'grid':
                self.consume('KEYWORD', 'grid')
                row_tok = self.consume('IDENTIFIER')
                col_tok = self.consume('IDENTIFIER')
                ast["grid"] = {"row_order": row_tok[1], "col_order": col_tok[1]}
            elif val == 'bounds':
                self.consume('KEYWORD', 'bounds')
                self.consume('IDENTIFIER', 'lat')
                lat_min = float(self.consume('NUMBER')[1])
                lat_max = float(self.consume('NUMBER')[1])
                self.consume('IDENTIFIER', 'lon')
                lon_min = float(self.consume('NUMBER')[1])
                lon_max = float(self.consume('NUMBER')[1])
                ast["bounds"] = {
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max
                }
            elif val == 'encoding':
                self.consume('KEYWORD', 'encoding')
                enc_type = self.consume('IDENTIFIER')[1]
                self.consume('LBRACE')
                scale, offset, nodata = 1.0, 0.0, -32768
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param = self.consume('KEYWORD')[1]
                    num_val = float(self.consume('NUMBER')[1])
                    if param == 'scale':
                        scale = num_val
                    elif param == 'offset':
                        offset = num_val
                    elif param == 'nodata':
                        nodata = int(num_val)
                self.consume('RBRACE')
                ast["encoding"] = {
                    "type": enc_type,
                    "scale": scale,
                    "offset": offset,
                    "nodata_value": nodata
                }
            elif val == 'level':
                self.consume('KEYWORD', 'level')
                lvl_num = int(self.consume('NUMBER')[1])
                self.consume('LBRACE')
                lvl_data = {"level": lvl_num}
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param = self.consume('KEYWORD')[1]
                    if param == 'elevation':
                        lvl_data["path"] = self.consume('STRING')[1]
                    elif param == 'shape':
                        h = int(self.consume('NUMBER')[1])
                        w = int(self.consume('NUMBER')[1])
                        lvl_data["shape"] = [h, w]
                    elif param == 'cell_size_deg':
                        lvl_data["cell_size_deg"] = float(self.consume('NUMBER')[1])
                    elif param in ['valid_mask', 'land_fraction', 'water_fraction']:
                        lvl_data[param] = self.consume('STRING')[1]
                    elif param == 'minmax':
                        path = self.consume('STRING')[1]
                        self.consume('KEYWORD', 'scope')
                        scope = self.consume('IDENTIFIER')[1]
                        lvl_data["minmax_path"] = path
                        lvl_data["minmax_scope"] = scope
                self.consume('RBRACE')
                ast["levels"].append(lvl_data)
            else:
                raise SyntaxError(f"[PARSER ERROR] 語法錯誤：未預期的語法關鍵字 '{val}' 於第 {tok[2]} 行")
                
        self.consume('RBRACE')
        return ast

def parse_code(code):
    """解析字串代碼，輸出 AST"""
    # 限制大小，防範 Memory Bomb
    if len(code) > 10 * 1024 * 1024: # 10MB
        raise ValueError("輸入檔案大小超出 10MB 安全限制！")
        
    tokens = tokenize(code)
    parser = SkinSpecParser(tokens)
    return parser.parse()

if __name__ == "__main__":
    # 輕量測試
    test_dsl = """
    skin terrain test_asset {
      schema rrkal.renderer_skin_asset.v0.2.2
      source SYNTHETIC_V2
      projection EPSG:4326
      grid south_to_north west_to_east
      bounds lat -90 90 lon -180 180
      encoding int16_meter {
        scale 0.5
        offset 0.0
        nodata -32768
      }
      level 0 {
        elevation payloads/elev.npz
        shape 180 360
        cell_size_deg 1.0
        valid_mask payloads/mask.npz
        land_fraction payloads/land.npz
        water_fraction payloads/water.npz
        minmax payloads/minmax.npz scope global_lod_summary
      }
    }
    """
    try:
        ast = parse_code(test_dsl)
        print("[+] 測試解析順利成功，AST 如下:")
        import json
        print(json.dumps(ast, indent=2))
    except Exception as e:
        print(f"[X] 解析測試失敗: {e}")
