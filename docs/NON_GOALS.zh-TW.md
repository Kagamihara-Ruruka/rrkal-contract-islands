# 非本階段與排斥目標 (Non-goals)

本文件明確界定 `rrkal-contract-islands`（全域契約語法糖實驗室）在第一階段以及未來長期演進中**堅決不予以實施的排斥目標 (Non-goals)**。這能防止專案職責過度膨脹，避免重演巨型單體代碼的過載瓶頸。

---

## 1. 執行期與 Runtime 面向的 Non-goals

* **不做 Python 方言 (No Python Dialect)**：
  本專案絕非 Python 語法的延伸或變體，不承諾與 Python 語法相容，更不實作任何動態 runtime 解釋器。
* **無侵入式 import hook (No Import / AST Injection)**：
  堅決不在 Python 的 `sys.meta_path` 中註冊自訂的加載器或 `import hook`。我們不支援諸如 `import terrain_synthetic.skinisland` 的侵入性動態加載語法。
* **不做 runtime 逆向編譯 (No JIT / No Transpiler)**：
  不實作任何執行期的 JIT 編譯或將島嶼語法糖編譯為 Python bytecode / 二進位代碼的行為。它僅在離線 (Offline) 或建置期 (Build Time) 作為靜態 JSON 生成工具。
* **無執行期依賴注入 (No Dependency Injection)**：
  解析器與編譯器運作時，絕不從外部環境、環境變數或資料庫中隱性注入、加載或依賴任何未明確聲明的 Python 類別或模組。

---

## 2. 產品對接與整合面向的 Non-goals

* **不干涉產品 Repo 代碼 (No Product Repo Edits)**：
  本專案 100% 保持在外部實驗階段。我們絕不嘗試將編譯器代碼直接合併、打包或以任何方式注入至三大產品 Repo（`APIkeys_collection`、`rrkal-visual-compressor`、`RRKAL_displaytools`）中。
* **不為產品 Repo 提供執行期庫 (No Runtime Library for Products)**：
  本專案不以 `pip` 套件、模組或 SDK 的形式供產品 Repo 引用。產品 Repo 與本專案的唯一物理界面，就是那一份由本專案離線生成並通過安全檢驗的 `manifest.json` 與 `RenderLayerSpec.json` 靜態檔案。
* **不執行自動化的遠端產品部署 (No Automatic Product Delivery)**：
  本專案不建立任何自動將產出 JSON 寫入或覆蓋至產品專案目錄下的流水線，所有產出均被物理限制在本實驗專案的內部目錄樹（如 `islands/**/examples/`）內，交由 Owner 核准後，方能以手動或安全配置方式引用。
