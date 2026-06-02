#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_skin_spec.py
功能：手寫 SkinSpec Island DSL 的 Tokenizer 與遞迴下降語法解析器。
特點：
1. 零第三方庫依賴 (zero-dependency)。
2. 100% 物理杜絕 eval/exec/__import__ 等動態指令執行漏洞。
3. 極限精密化：支援精確列號 (col_num) 起止記錄與 Caret Trace 錯誤回溯診斷。
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

def format_error_trace(code, line_num, col_num, message):
    """將錯誤格式化為帶有精確 Caret (^) 指標與代碼行回溯的訊息"""
    if not code:
        return f"{message} 於第 {line_num} 行，位置 {col_num}"
    lines = code.split('\n')
    if 1 <= line_num <= len(lines):
        error_line = lines[line_num - 1]
        # 用來精確指向
        caret_line = ' ' * (col_num - 1) + '^'
        return f"{message}\n    在第 {line_num} 行，位置 {col_num}：\n    {error_line}\n    {caret_line}"
    return f"{message} (於第 {line_num} 行，位置 {col_num})"

def tokenize(code):
    """安全詞法掃描器：切碎 Tokens，不調用 eval，精確保留起止列號 pos + 1"""
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
                # 拋出帶有 Caret Trace 的語法錯誤
                msg = format_error_trace(code, line_num, pos + 1, f"[LEXER ERROR] 發現非法字元 '{line[pos]}'")
                raise SyntaxError(msg)
    return tokens

class SkinSpecParser:
    """遞迴下降解析器 (Recursive Descent Parser)，附加物理 _meta 坐標追蹤"""
    def __init__(self, tokens, code):
        self.tokens = tokens
        self.code = code
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
            msg = format_error_trace(
                self.code, line, pos, 
                f"[PARSER ERROR] 語法錯誤：預期 Token 型態為 {expected_type}，但得到 {tok_type} ('{val}')"
            )
            raise SyntaxError(msg)
            
        if expected_val and val != expected_val:
            msg = format_error_trace(
                self.code, line, pos, 
                f"[PARSER ERROR] 語法錯誤：預期值為 '{expected_val}'，但得到 '{val}'"
            )
            raise SyntaxError(msg)
            
        self.idx += 1
        return tok

    def parse(self):
        """主解析入口，精確注入 _meta 坐標"""
        skin_tok = self.consume('KEYWORD', 'skin')
        kind_tok = self.consume('IDENTIFIER')
        id_tok = self.consume('IDENTIFIER')
        self.consume('LBRACE')
        
        ast = {
            "kind": kind_tok[1],
            "asset_id": id_tok[1],
            "levels": [],
            "_meta": {
                "skin": (skin_tok[2], skin_tok[3]),
                "kind": (kind_tok[2], kind_tok[3]),
                "asset_id": (id_tok[2], id_tok[3]),
            }
        }
        
        while self.peek() and self.peek()[0] != 'RBRACE':
            tok = self.peek()
            val = tok[1]
            if val == 'schema':
                self.consume('KEYWORD', 'schema')
                val_tok = self.consume('IDENTIFIER')
                ast["schema"] = val_tok[1]
                ast["_meta"]["schema"] = (val_tok[2], val_tok[3])
            elif val == 'source':
                self.consume('KEYWORD', 'source')
                val_tok = self.consume('IDENTIFIER')
                ast["source_dataset"] = val_tok[1]
                ast["_meta"]["source_dataset"] = (val_tok[2], val_tok[3])
            elif val == 'projection':
                self.consume('KEYWORD', 'projection')
                val_tok = self.consume('IDENTIFIER')
                ast["projection"] = {"system": val_tok[1]}
                ast["_meta"]["projection"] = (val_tok[2], val_tok[3])
            elif val == 'grid':
                self.consume('KEYWORD', 'grid')
                row_tok = self.consume('IDENTIFIER')
                col_tok = self.consume('IDENTIFIER')
                ast["grid"] = {"row_order": row_tok[1], "col_order": col_tok[1]}
                ast["_meta"]["grid"] = (row_tok[2], row_tok[3])
            elif val == 'bounds':
                bounds_tok = self.consume('KEYWORD', 'bounds')
                self.consume('IDENTIFIER', 'lat')
                lat_min_tok = self.consume('NUMBER')
                lat_max_tok = self.consume('NUMBER')
                self.consume('IDENTIFIER', 'lon')
                lon_min_tok = self.consume('NUMBER')
                lon_max_tok = self.consume('NUMBER')
                ast["bounds"] = {
                    "lat_min": float(lat_min_tok[1]),
                    "lat_max": float(lat_max_tok[1]),
                    "lon_min": float(lon_min_tok[1]),
                    "lon_max": float(lon_max_tok[1])
                }
                ast["_meta"]["bounds"] = (bounds_tok[2], bounds_tok[3])
            elif val == 'encoding':
                enc_tok = self.consume('KEYWORD', 'encoding')
                enc_type = self.consume('IDENTIFIER')[1]
                self.consume('LBRACE')
                scale, offset, nodata = 1.0, 0.0, -32768
                scale_meta, offset_meta, nodata_meta = None, None, None
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param_tok = self.consume('KEYWORD')
                    param = param_tok[1]
                    num_tok = self.consume('NUMBER')
                    num_val = float(num_tok[1])
                    if param == 'scale':
                        scale = num_val
                        scale_meta = (param_tok[2], param_tok[3])
                    elif param == 'offset':
                        offset = num_val
                        offset_meta = (param_tok[2], param_tok[3])
                    elif param == 'nodata':
                        nodata = int(num_val)
                        nodata_meta = (param_tok[2], param_tok[3])
                self.consume('RBRACE')
                ast["encoding"] = {
                    "type": enc_type,
                    "scale": scale,
                    "offset": offset,
                    "nodata_value": nodata
                }
                ast["_meta"]["encoding"] = (enc_tok[2], enc_tok[3])
                if scale_meta: ast["_meta"]["encoding_scale"] = scale_meta
                if offset_meta: ast["_meta"]["encoding_offset"] = offset_meta
                if nodata_meta: ast["_meta"]["encoding_nodata"] = nodata_meta
            elif val == 'level':
                level_tok = self.consume('KEYWORD', 'level')
                lvl_num_tok = self.consume('NUMBER')
                lvl_num = int(lvl_num_tok[1])
                self.consume('LBRACE')
                lvl_data = {"level": lvl_num}
                lvl_meta = {
                    "level_num": (lvl_num_tok[2], lvl_num_tok[3])
                }
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param_tok = self.consume('KEYWORD')
                    param = param_tok[1]
                    if param == 'elevation':
                        val_tok = self.consume('STRING')
                        lvl_data["path"] = val_tok[1]
                        lvl_meta["elevation"] = (val_tok[2], val_tok[3])
                    elif param == 'shape':
                        h_tok = self.consume('NUMBER')
                        w_tok = self.consume('NUMBER')
                        lvl_data["shape"] = [int(h_tok[1]), int(w_tok[1])]
                        lvl_meta["shape"] = (param_tok[2], param_tok[3])
                    elif param == 'cell_size_deg':
                        val_tok = self.consume('NUMBER')
                        lvl_data["cell_size_deg"] = float(val_tok[1])
                        lvl_meta["cell_size_deg"] = (param_tok[2], param_tok[3])
                    elif param in ['valid_mask', 'land_fraction', 'water_fraction']:
                        val_tok = self.consume('STRING')
                        lvl_data[param] = val_tok[1]
                        lvl_meta[param] = (val_tok[2], val_tok[3])
                    elif param == 'minmax':
                        val_tok = self.consume('STRING')
                        self.consume('KEYWORD', 'scope')
                        scope_tok = self.consume('IDENTIFIER')
                        lvl_data["minmax_path"] = val_tok[1]
                        lvl_data["minmax_scope"] = scope_tok[1]
                        lvl_meta["minmax"] = (param_tok[2], param_tok[3])
                self.consume('RBRACE')
                lvl_data["_meta"] = lvl_meta
                ast["levels"].append(lvl_data)
            else:
                msg = format_error_trace(self.code, tok[2], tok[3], f"[PARSER ERROR] 語法錯誤：未預期的語法關鍵字 '{val}'")
                raise SyntaxError(msg)
                
        self.consume('RBRACE')
        return ast

def parse_code(code):
    """解析字串代碼，輸出 AST，附帶物理 _meta 坐標"""
    if len(code) > 10 * 1024 * 1024: # 10MB
        raise ValueError("輸入檔案大小超出 10MB 安全限制！")
        
    tokens = tokenize(code)
    parser = SkinSpecParser(tokens, code)
    return parser.parse()

if __name__ == "__main__":
    test_dsl = """
    skin terrain test_asset {
      schema rrkal.renderer_skin_asset.v0.2.2
      bounds lat -90 90 lon -180 180
      level 0 {
        shape 180 360
      }
    }
    """
    try:
        ast = parse_code(test_dsl)
        print("[+] 測試解析順利成功，AST 如下:")
        import json
        print(json.dumps(ast, indent=2))
    except Exception as e:
        print(f"[X] 解析測試失敗:\n{e}")
