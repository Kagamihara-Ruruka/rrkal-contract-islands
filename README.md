# rrkal-contract-islands: RRKAL 全域契約語法糖實驗室

本專案為 **`rrkal-contract-islands`（RRKAL 全域契約語法糖實驗室）**。它純粹作為一個 **「RRKAL contract authoring sugar」（RRKAL 契約撰寫語法糖）**，旨在提供更直覺、人類可讀的聲明式語法糖（如 `.skinisland`），用以靜態編譯並產生既有的標準 RRKAL JSON 契約（如 `manifest.json`）。

> [!IMPORTANT]
> **Owner 上下文提醒與邊界紅線（100% 遵循）：**
> 1. **唯一合法定位**：本任務**不是**要做 RRKAL 的新程式語言，**不是** Python 方言，也**不是** runtime transpiler。它僅被定位為「RRKAL contract authoring sugar」，用比較人類可讀的宣告語法產生既有的 RRKAL JSON。它不創造任何新的 runtime truth，只編譯成靜態的 JSON 契約檔。
> 2. **獨立外部 Repo 定位**：為確保「全域契約語法糖」實驗能力不污染 `vis_2_dis`（壓縮層/皮層/渲染層之間的 RendererSkinAsset 外部 reference prototype），本專案物理隔離於獨立倉庫 `rrkal-contract-islands` 中，不塞入 `vis_2_dis` 主線。
> 3. **產品專案 100% 唯讀**：本專案對以下四大產品與原型專案保持 100% 唯讀存取，嚴禁任何形式的寫入或修改：
>    * `APIkeys_collection`
>    * `rrkal-visual-compressor`
>    * `RRKAL_displaytools`
>    * `vis_2_dis` (外部皮層原型基準線)
>    嚴禁開啟這些產品專案的 branch/PR、嚴禁生成產品文件或進行任何產品 integration。
> 4. **嚴格 Non-goals**：**No eval, No exec, No import hook, No Python AST rewrite, No runtime transpiler, No monkeypatch, No Python dialect, No dependency injection, No shell command execution, No arbitrary file writes outside output dir.** 本專案僅是外部靜態 parser 雛形，不具備任何執行期副作用。
> 5. **第一階段 SkinSpec Island 範本限制**：僅支援將皮層契約語法（`.skinisland`）靜態解析並編譯為與 `RendererSkinAsset` 相容的 JSON manifest，不輸出任何 Python 程式碼，不執行任何程式碼。
> 6. **Parser 極致安全與零依賴**：詞法掃描與語法解析完全為零依賴或 Python 標準庫優先，手寫 Tokenizer 與 Parser，不調用任何危險動態求值函數。

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
