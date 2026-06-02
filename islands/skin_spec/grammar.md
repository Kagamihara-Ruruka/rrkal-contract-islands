# SkinSpec Island 語法與詞法規範 (Grammar & Lexer Spec)

本文件詳細定義 **`SkinSpec Island`** 的詞法 Token 與語法結構規範。

---

## 1. 詞法 Token 定義 (Lexer Spec)

詞法分析器 (Lexer) 純粹使用內建 Regex 分詞，排斥任意動態指令執行。Token 匹配規則定義如下：

| Token 種類 | 正則匹配規則 | 語意說明 | 範例 |
| --- | --- | --- | --- |
| `COMMENT` | `#.*` | 註解，分詞時會被安全過濾 | `# 這是一行註解` |
| `LBRACE` | `\{` | 左大括弧，表示區域嵌套開始 | `{` |
| `RBRACE` | `\}` | 右大括弧，表示區域嵌套結束 | `}` |
| `NUMBER` | `-?\d+(?:\.\d+)?` | 數字，支援負數與浮點數 | `0.5`, `-32768` |
| `KEYWORD` | 見下方關鍵字列表 | 保留之核心宣告鍵 | `skin`, `encoding`, `level` |
| `IDENTIFIER` | `\b[a-zA-Z_][a-zA-Z0-9_\.:]*\b` | 識別碼，字元組合（支援句點與冒號） | `terrain`, `EPSG:4326`, `v0.2.2` |
| `STRING` | `[a-zA-Z0-9_\-\./]+` | 字串路徑，不含引號之 DSL 路徑字元 | `payloads/elevation_l0_i16.npz` |
| `WS` | `\s+` | 空白與換行，分詞時被過濾 | `\n`, ` ` |

### 核心關鍵字列表：
`skin`, `schema`, `source`, `projection`, `grid`, `bounds`, `encoding`, `level`, `scale`, `offset`, `nodata`, `elevation`, `shape`, `cell_size_deg`, `valid_mask`, `land_fraction`, `water_fraction`, `minmax`, `scope`

---

## 2. 語法結構規範 (EBNF-like Syntax)

語法嵌套邏輯以聲明式結構表示，定義如下：

```text
SkinIsland  ::= 'skin' kind asset_id '{' Decl* '}'
Decl        ::= SchemaDecl | SourceDecl | ProjDecl | GridDecl | BoundsDecl | EncodingDecl | LevelDecl

SchemaDecl  ::= 'schema' identifier
SourceDecl  ::= 'source' identifier
ProjDecl    ::= 'projection' identifier
GridDecl    ::= 'grid' row_order col_order
BoundsDecl  ::= 'bounds' 'lat' number number 'lon' number number

EncodingDecl::= 'encoding' identifier '{' EncParam* '}'
EncParam    ::= 'scale' number | 'offset' number | 'nodata' number

LevelDecl   ::= 'level' number '{' LevelParam* '}'
LevelParam  ::= 'elevation' string
              | 'shape' number number
              | 'cell_size_deg' number
              | 'valid_mask' string
              | 'land_fraction' string
              | 'water_fraction' string
              | 'minmax' string 'scope' identifier
```

---

## 3. AST (抽象語法樹) 映射 JSON 規則

解析器產出之 AST 為嵌套之 Python 字典，編譯器將其轉換為合規 JSON：

* **`skin <kind> <id> {}`** -> 映射至 JSON 的頂層 `"kind": kind`, `"asset_id": id`，且 status 默認為 `"ready"`。
* **`grid <row> <col>`** -> 映射至 `"grid": {"row_order": row, "col_order": col, "bounds_semantics": "grid_points_inclusive", "lon_wrap": "[-180,180]"}`。
* **`bounds lat <y1> <y2> lon <x1> <x2>`** -> 映射至 `"bounds": {"lat_min": y1, "lat_max": y2, "lon_min": x1, "lon_max": x2}`。
* **`encoding <type> {}`** -> 映射至 `"encoding": {"type": type, "scale": scale, "offset": offset, "nodata_value": nodata}`。
* **`level <num> {}`** -> 映射至 `"levels"` 陣列中的對應層級物件：
  - `elevation` -> 映射至 `"path"`
  - `shape <h> <w>` -> 映射至整數陣列 `"shape": [h, w]`，且 `"raw_nbytes"` 自動推導為 $h \times w \times 2$
  - `minmax <path> scope <scope>` -> 映射至 `"minmax_path": path`, `"minmax_scope": scope`
  - 其他如 `valid_mask`、`land_fraction`、`water_fraction` 映射至對應的二進位覆蓋路徑。
