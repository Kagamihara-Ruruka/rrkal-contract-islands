# rrkal-contract-islands: RRKAL 全域契約語法糖實驗室

本專案為 **`rrkal-contract-islands`（RRKAL 全域契約語法糖實驗室）**。它純粹作為一個 declarative 契約編譯器，將簡潔、人類可讀且甜美的島嶼契約語法糖（`.skinisland`、`.layerisland` 等）解析並編譯輸出為標準、合規且可被驗證的 JSON 契約（如 `manifest.json` 與 `RenderLayerSpec.json`）。

---

## 1. 核心定位與設計邊界 (Core Position & Boundaries)

> [!IMPORTANT]
> **本實驗室專案嚴格遵守以下安全與物理紅線，絕不妥協：**
> 1. **非程式語言 Runtime (No Python Dialect / No AST Runtime)**：本專案僅是文字編譯器，不創造 Python 方言，**不實作任何隱性的 `import hook` 或 `sys.meta_path` 重寫，亦不修改 Python 的執行期 AST**。
> 2. **零執行期安全漏洞 (No eval / No exec)**：解析與編譯流程純粹基於正則分詞（Regex Tokenizer）與手寫遞迴下降語法解析（Recursive Descent Parser），**100% 物理杜絕調用 `eval()`、`exec()`、`__import__()` 或是執行任意 shell 腳本**，保障全域安全性。
> 3. **產品專案 100% 唯讀**：任何情況下均嚴禁主動修改三個主要產品 Repo (`APIkeys_collection`、`rrkal-visual-compressor`、`RRKAL_displaytools`)，維持絕對唯讀的物理防護。
> 4. **零依賴性解耦 (Zero-dependency Decoupling)**：本專案為獨立實驗室，產品專案只需在 Ingestion 時讀取由本專案編譯產出的標準 JSON 契約（如 `manifest.json`），**產品專案的代碼絕對不依賴本專案任何模組**，保證系統依賴性降至最低。

---

## 2. 目錄與專案結構

```text
rrkal-contract-islands/
├── README.md                                       # 本說明文件
├── docs/
│   ├── DESIGN_PRINCIPLES.zh-TW.md                  # 設計哲學與邊界定義
│   ├── NON_GOALS.zh-TW.md                          # 非本階段與未來排斥目標
│   └── OWNER_REPO_ACCESS_POLICY.zh-TW.md           # 唯讀存取政策與安全邊界防禦
├── islands/
│   └── skin_spec/
│       ├── README.md                               # SkinSpec 島嶼說明
│       ├── grammar.md                              # 詞法與語法 DSL 規範
│       ├── examples/
│       │   ├── terrain_synthetic.skinisland        # 語法糖輸入原始檔
│       │   └── terrain_synthetic.expected.json     # 期望編譯產出之 JSON
│       └── reference_python/
│           ├── parse_skin_spec.py                  # zero-dependency 手寫 Tokenizer/Parser
│           ├── compile_skin_spec.py                # AST 轉 JSON 編譯器
│           └── validate_output.py                  # 產出驗證與 Ingestion 聯鎖測試
├── schemas/
│   └── renderer_skin_asset.v0.2.2.schema.json      # Ingestion 約定之 JSON Schema
├── tests/
│   └── test_compiler.py                            # 語法編譯端到端自動化測試
└── AGENT_HANDOFF.zh-TW.md                          # 接力卡文檔
```

---

## 3. 快速開始 (Quick Start)

### 3.1 編譯 SkinSpec 語法糖
在專案根目錄下，您可以呼叫參考 Python 編譯器，將 `.skinisland` 編譯輸出為合規之 `manifest.json`：
```bash
python3 islands/skin_spec/reference_python/compile_skin_spec.py \
  --input islands/skin_spec/examples/terrain_synthetic.skinisland \
  --output islands/skin_spec/examples/manifest.json
```

### 3.2 執行 Ingestion 聯鎖測試
校驗編譯產出是否符合 `vis_2_dis` 原型之 v0.2.2 安全 Ingestion 驗證規範：
```bash
python3 islands/skin_spec/reference_python/validate_output.py
```

---

## 4. Owner 審批與產品化政策 (Owner Approval Policy)

* **審批狀態**：**本專案已獲得 Owner 明確書面與指令批准，授權在 `rrkal-contract-islands` 本外部實驗倉庫中進行編置與代碼實裝。**
* **產品化限制**：本實驗室所有代碼與語法糖**尚未授權實裝於任何產品 Repo**。本專案之編譯成果目前僅作為開源與跨 Agent 協同討論的「技術語法糖參考」（reference baseline），不進行任何自動化的產品主線整合。
