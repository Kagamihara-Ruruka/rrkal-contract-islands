# SkinSpec Island - 皮層契約語法糖

> [!IMPORTANT]
> **專案治理與非送審聲明：**
> * **非生產環境就緒 (Not production-ready)**：本實驗專案產出之代碼與工具僅作為外部原型參考（external reference prototype），絕非生產就緒代碼。
> * **未授權合併產品 Repo (Not authorized for product repo integration)**：嚴禁將本專案的 any 編譯或工具代碼併入三大產品倉庫中，主線倉庫維持唯讀。
> * **需要 O_1 審查 (Requires o_1 review before product adoption)**：本專案之機制若要被產品主線採用，必須經過 `o_1` 進行嚴格審查與正式授權。

本目錄為 **`SkinSpec Island`** 的專屬語法實驗室，負責定義與實現「地形與皮層資產 (RendererSkinAsset)」的聲明式語法糖。

---

## 1. 目錄結構

```text
skin_spec/
├── README.md                               # 本說明文件
├── grammar.md                              # 詞法與語法 DSL 規範
├── examples/
│   ├── terrain_synthetic.skinisland        # 語法糖輸入原始檔
│   └── terrain_synthetic.expected.json     # 期望編譯產出之 JSON
└── reference_python/
    ├── parse_skin_spec.py                  # zero-dependency 手寫 Tokenizer/Parser
    ├── compile_skin_spec.py                # AST 轉 JSON 編譯器
    └── validate_output.py                  # 產出驗證與 Ingestion 聯鎖測試
```

---

## 2. 第一階段實作目標

透過 DSL 聲明 `terrain_synthetic.skinisland`，編譯器在排除 eval/exec 執行風險的前提下，生成符合 `RendererSkinAsset v0.2.2` 規格（作為 reference baseline）的 `manifest.json`，並能夠通過 `vis_2_dis` 的 Ingestion 驗證器的基本測試（smoke passed under current test scope，external reference prototype pass with notes）。
