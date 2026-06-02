# LayerSpec Island 語法與詞法規範 (Grammar & Lexer Spec)

本文件詳細定義 **`LayerSpec Island`** 的詞法 Token 與語法結構規範。

---

## 1. 詞法 Token 定義 (Lexer Spec)

詞法分析器 (Lexer) 純粹使用內建 Regex 分詞，排斥任意動態指令執行。Token 匹配規則定義如下：

| Token 種類 | 正則匹配規則 | 語意說明 | 範例 |
| --- | --- | --- | --- |
| `COMMENT` | `#.*` | 註解，分詞時會被安全過濾 | `# 這是一行註解` |
| `LBRACE` | `\{` | 左大括弧，表示區域嵌套開始 | `{` |
| `RBRACE` | `\}` | 右大括弧，表示區域嵌套結束 | `}` |
| `NUMBER` | `-?\d+(?:\.\d+)?` | 數字，支援負數與浮點數 | `1.0`, `255` |
| `BOOLEAN` | `\b(?:true|false)\b` | 布林值，對應 Python 布林型態 | `true`, `false` |
| `KEYWORD` | 見下方關鍵字列表 | 保留之核心宣告鍵 | `layer`, `lod_policy`, `coverage` |
| `IDENTIFIER` | `\b[a-zA-Z_][a-zA-Z0-9_\.:]*\b` | 識別碼，字元組合（支援句點與冒號） | `synthetic_terrain_layer`, `v0.2.1` |
| `STRING` | `[a-zA-Z0-9_\-\./]+` | 字串路徑，不含引號之 DSL 路徑字元 | `skins/terrain/manifest.json` |
| `WS` | `\s+` | 空白與換行，分詞時被過濾 | `\n`, ` ` |

### 核心關鍵字列表：
`layer`, `schema`, `layer_id`, `layer_type`, `source_skin_asset`, `source_manifest`, `visible`, `opacity`, `blend_mode`, `render_queue_group`, `lod_policy`, `mode`, `interactive_level`, `preview_level`, `quality_level`, `export_level`, `coverage`, `coverage_mask_kind`, `resolve_by_lod`, `opaque_mask`, `opaque_mask_kind`, `threshold`, `requires_underlay`, `update_policy`, `interactive`, `settled`, `export`, `status`

---

## 2. 語法結構規範 (EBNF-like Syntax)

語法嵌套邏輯以聲明式結構表示，定義如下：

```text
LayerSpec           ::= 'layer' layer_name '{' Decl* '}'
Decl                ::= SchemaDecl 
                      | LayerIdDecl 
                      | LayerTypeDecl 
                      | SourceSkinDecl 
                      | SourceManifestDecl 
                      | VisibleDecl 
                      | OpacityDecl 
                      | BlendModeDecl 
                      | QueueGroupDecl 
                      | LodPolicyDecl 
                      | CoverageDecl 
                      | UpdatePolicyDecl 
                      | StatusDecl

SchemaDecl          ::= 'schema' identifier
LayerIdDecl         ::= 'layer_id' identifier
LayerTypeDecl       ::= 'layer_type' identifier
SourceSkinDecl      ::= 'source_skin_asset' identifier
SourceManifestDecl  ::= 'source_manifest' string
VisibleDecl         ::= 'visible' boolean
OpacityDecl         ::= 'opacity' number
BlendModeDecl       ::= 'blend_mode' identifier
QueueGroupDecl      ::= 'render_queue_group' identifier
StatusDecl          ::= 'status' identifier

LodPolicyDecl       ::= 'lod_policy' '{' LodParam* '}'
LodParam            ::= 'mode' identifier
                      | 'interactive_level' number
                      | 'preview_level' number
                      | 'quality_level' number
                      | 'export_level' number

CoverageDecl        ::= 'coverage' '{' CoverageParam* '}'
CoverageParam       ::= 'coverage_mask_kind' identifier
                      | 'resolve_by_lod' boolean
                      | 'requires_underlay' boolean
                      | 'opaque_mask' '{' OpaqueParam* '}'

OpaqueParam         ::= 'opaque_mask_kind' identifier
                      | 'threshold' number

UpdatePolicyDecl    ::= 'update_policy' '{' UpdateParam* '}'
UpdateParam         ::= 'interactive' identifier
                      | 'settled' identifier
                      | 'export' identifier
```

---

## 3. AST (抽象語法樹) 映射 JSON 規則

解析器產出之 AST 為嵌套之 Python 字典，編譯器將其轉換為與 `displaytools` 規格 100% 相容之 JSON：

* **`layer <name> {}`** -> AST 頂層容器，對應 JSON 輸出。
* **`visible <boolean>`** -> 轉換為 JSON 實體布林型態 `true` / `false`。
* **`opacity <number>`** -> 轉換為浮點數 `float`。
* **`lod_policy` / `coverage` / `update_policy`** -> 映射至 JSON 的嵌套物件。
* **`opaque_mask`** -> 嵌套於 `coverage` 下的物件。
* **`threshold <number>`** -> 轉換為整數 `int`。
* **`interactive_level` / `preview_level` / `quality_level` / `export_level`** -> 轉換為整數 `int`。
