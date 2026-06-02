#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_layer_spec.py
功能：手寫 LayerSpec DSL 的 Tokenizer 與遞迴下降語法解析器。
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
    ('BOOLEAN',    r'\b(?:true|false)\b'),
    ('NUMBER',     r'-?\d+(?:\.\d+)?'),
    # 限制 STRING 必須至少包含一個斜線、點號或破折號，以與純單字區分，並置於最前以最長匹配
    ('STRING',     r'[a-zA-Z0-9_\-\./]*[\./\-][a-zA-Z0-9_\-\./]*'),
    ('KEYWORD',    r'\b(?:layer|schema|layer_id|layer_type|source_skin_asset|source_manifest|visible|opacity|blend_mode|render_queue_group|lod_policy|mode|interactive_level|preview_level|quality_level|export_level|coverage|coverage_mask_kind|resolve_by_lod|opaque_mask|opaque_mask_kind|threshold|requires_underlay|update_policy|interactive|settled|export|status)\b'),
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

class LayerSpecParser:
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
        layer_tok = self.consume('KEYWORD', 'layer')
        name_tok = self.consume('IDENTIFIER')
        self.consume('LBRACE')
        
        ast = {
            "layer_name": name_tok[1],
            "_meta": {
                "layer": (layer_tok[2], layer_tok[3]),
                "layer_name": (name_tok[2], name_tok[3]),
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
            elif val == 'layer_id':
                self.consume('KEYWORD', 'layer_id')
                val_tok = self.consume('IDENTIFIER')
                ast["layer_id"] = val_tok[1]
                ast["_meta"]["layer_id"] = (val_tok[2], val_tok[3])
            elif val == 'layer_type':
                self.consume('KEYWORD', 'layer_type')
                val_tok = self.consume('IDENTIFIER')
                ast["layer_type"] = val_tok[1]
                ast["_meta"]["layer_type"] = (val_tok[2], val_tok[3])
            elif val == 'source_skin_asset':
                self.consume('KEYWORD', 'source_skin_asset')
                val_tok = self.consume('IDENTIFIER')
                ast["source_skin_asset"] = val_tok[1]
                ast["_meta"]["source_skin_asset"] = (val_tok[2], val_tok[3])
            elif val == 'source_manifest':
                self.consume('KEYWORD', 'source_manifest')
                val_tok = self.consume('STRING')
                ast["source_manifest"] = val_tok[1]
                ast["_meta"]["source_manifest"] = (val_tok[2], val_tok[3])
            elif val == 'visible':
                self.consume('KEYWORD', 'visible')
                val_tok = self.consume('BOOLEAN')
                ast["visible"] = (val_tok[1] == 'true')
                ast["_meta"]["visible"] = (val_tok[2], val_tok[3])
            elif val == 'opacity':
                self.consume('KEYWORD', 'opacity')
                val_tok = self.consume('NUMBER')
                ast["opacity"] = float(val_tok[1])
                ast["_meta"]["opacity"] = (val_tok[2], val_tok[3])
            elif val == 'blend_mode':
                self.consume('KEYWORD', 'blend_mode')
                val_tok = self.consume('IDENTIFIER')
                ast["blend_mode"] = val_tok[1]
                ast["_meta"]["blend_mode"] = (val_tok[2], val_tok[3])
            elif val == 'render_queue_group':
                self.consume('KEYWORD', 'render_queue_group')
                val_tok = self.consume('IDENTIFIER')
                ast["render_queue_group"] = val_tok[1]
                ast["_meta"]["render_queue_group"] = (val_tok[2], val_tok[3])
            elif val == 'status':
                self.consume('KEYWORD', 'status')
                val_tok = self.consume('IDENTIFIER')
                ast["status"] = val_tok[1]
                ast["_meta"]["status"] = (val_tok[2], val_tok[3])
            elif val == 'lod_policy':
                lod_tok = self.consume('KEYWORD', 'lod_policy')
                self.consume('LBRACE')
                lod_policy = {}
                lod_meta = {}
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param_tok = self.consume('KEYWORD')
                    param = param_tok[1]
                    if param == 'mode':
                        val_tok = self.consume('IDENTIFIER')
                        lod_policy["mode"] = val_tok[1]
                        lod_meta["mode"] = (val_tok[2], val_tok[3])
                    elif param in ['interactive_level', 'preview_level', 'quality_level', 'export_level']:
                        val_tok = self.consume('NUMBER')
                        lod_policy[param] = int(val_tok[1])
                        lod_meta[param] = (val_tok[2], val_tok[3])
                self.consume('RBRACE')
                ast["lod_policy"] = lod_policy
                ast["_meta"]["lod_policy"] = (lod_tok[2], lod_tok[3])
                ast["_meta"]["lod_policy_params"] = lod_meta
            elif val == 'coverage':
                cov_tok = self.consume('KEYWORD', 'coverage')
                self.consume('LBRACE')
                coverage = {}
                cov_meta = {}
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param_tok = self.consume('KEYWORD')
                    param = param_tok[1]
                    if param == 'coverage_mask_kind':
                        val_tok = self.consume('IDENTIFIER')
                        coverage["coverage_mask_kind"] = val_tok[1]
                        cov_meta["coverage_mask_kind"] = (val_tok[2], val_tok[3])
                    elif param == 'resolve_by_lod':
                        val_tok = self.consume('BOOLEAN')
                        coverage["resolve_by_lod"] = (val_tok[1] == 'true')
                        cov_meta["resolve_by_lod"] = (val_tok[2], val_tok[3])
                    elif param == 'requires_underlay':
                        val_tok = self.consume('BOOLEAN')
                        coverage["requires_underlay"] = (val_tok[1] == 'true')
                        cov_meta["requires_underlay"] = (val_tok[2], val_tok[3])
                    elif param == 'opaque_mask':
                        self.consume('LBRACE')
                        opaque_mask = {}
                        opaque_meta = {}
                        while self.peek() and self.peek()[0] != 'RBRACE':
                            op_param_tok = self.consume('KEYWORD')
                            op_param = op_param_tok[1]
                            if op_param == 'opaque_mask_kind':
                                val_tok = self.consume('IDENTIFIER')
                                opaque_mask["opaque_mask_kind"] = val_tok[1]
                                opaque_meta["opaque_mask_kind"] = (val_tok[2], val_tok[3])
                            elif op_param == 'threshold':
                                val_tok = self.consume('NUMBER')
                                opaque_mask["threshold"] = int(val_tok[1])
                                opaque_meta["threshold"] = (val_tok[2], val_tok[3])
                        self.consume('RBRACE')
                        coverage["opaque_mask"] = opaque_mask
                        cov_meta["opaque_mask"] = opaque_meta
                self.consume('RBRACE')
                ast["coverage"] = coverage
                ast["_meta"]["coverage"] = (cov_tok[2], cov_tok[3])
                ast["_meta"]["coverage_params"] = cov_meta
            elif val == 'update_policy':
                up_tok = self.consume('KEYWORD', 'update_policy')
                self.consume('LBRACE')
                update_policy = {}
                up_meta = {}
                while self.peek() and self.peek()[0] != 'RBRACE':
                    param_tok = self.consume('KEYWORD')
                    param = param_tok[1]
                    if param in ['interactive', 'settled', 'export']:
                        val_tok = self.consume('IDENTIFIER')
                        update_policy[param] = val_tok[1]
                        up_meta[param] = (val_tok[2], val_tok[3])
                self.consume('RBRACE')
                ast["update_policy"] = update_policy
                ast["_meta"]["update_policy"] = (up_tok[2], up_tok[3])
                ast["_meta"]["update_policy_params"] = up_meta
            else:
                msg = format_error_trace(self.code, tok[2], tok[3], f"[PARSER ERROR] 語法錯誤：未預期的語法關鍵字 '{val}'")
                raise SyntaxError(msg)
                
        self.consume('RBRACE')
        return ast

def parse_layer_code(code):
    """解析字串代碼，輸出 AST，附帶物理 _meta 坐標"""
    if len(code) > 10 * 1024 * 1024:  # 10MB
        raise ValueError("輸入檔案大小超出 10MB 安全限制！")
        
    tokens = tokenize(code)
    parser = LayerSpecParser(tokens, code)
    return parser.parse()

if __name__ == "__main__":
    test_dsl = """
    layer terrain_composite {
      schema rrkal_displaytools.render_layer_spec.v0.2.1
      opacity 1.0
      blend_mode normal
      coverage {
        opaque_mask {
          threshold 255
        }
      }
    }
    """
    try:
        ast = parse_layer_code(test_dsl)
        print("[+] 測試解析順利成功，AST 如下:")
        import json
        print(json.dumps(ast, indent=2))
    except Exception as e:
        print(f"[X] 解析測試失敗:\n{e}")
