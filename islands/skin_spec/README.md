# SkinSpec Island - 皮層契約語法糖

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

透過 DSL 聲明 `terrain_synthetic.skinisland`，編譯器能夠在 **100% 杜絕 eval/exec 執行漏洞** 的安全前提下，生成完全相容於 `RendererSkinAsset v0.2.2` 規格的 `manifest.json`，並能夠被 `vis_2_dis` 的 Ingestion 驗證器安全驗證。
