# 產品 Repo 唯讀存取政策與安全邊界防禦

> [!IMPORTANT]
> **專案治理與非生產聲明：**
> * **非生產環境就緒 (Not production-ready)**：本實驗專案產出之代碼與工具僅作為外部原型參考（external reference prototype），絕非生產就緒代碼。
> * **未授權合併產品 Repo (Not authorized for product repo integration)**：嚴禁將本專案的任何編譯或工具代碼併入三大產品倉庫中，主線倉庫維持唯讀。
> * **需要 O_1 審查 (Requires o_1 review before product adoption)**：本專案之機制若要被產品主線採用，必須經過 `o_1` 進行嚴格審查與正式授權。

本文件明確規定 `rrkal-contract-islands`（全域契約語法糖實驗室）在與主產品專案協同、自檢測試及執行過程中的產品 Repo 存取限制與物理邊界防禦政策。

---

## 1. 唯讀邊界宣告 (Read-Only Access Rule)

依據 Owner 2026-06-01 20:45 權威裁定，本專案在與其他專案互動時，必須無條件遵守以下物理防禦規定：

* **100% 外部專案與產品 Repo 唯讀**：
  本實驗室專案之所有測試、腳本及解析工具，對三大產品專案以及已凍結的外部皮層原型專案：
  1. `APIkeys_collection`
  2. `rrkal-visual-compressor`
  3. `RRKAL_displaytools`
  4. `vis_2_dis` (中介契約層外部參考原型基準線)
  皆僅擁有 **100% 唯讀（Read-Only）** 權限。嚴禁在任何測試套件或自動化腳本中包含對上述專案目錄進行 `write`、`delete`、`chmod` 或任何形式寫入的指令。
* **未偵測到本輪產品 Repo 修改**：
  在執行提交與 push 前，必須確保沒有任何與產品專案相關的變動被暫存或提交，切實捍衛產品專案的純淨性與代碼主權。

---

## 2. 安全邊界聯鎖防禦 (Sanitization & Defense Lock)

為防止測試和聯鎖腳本在引用外部校驗器時引發潛在寫入風險，我們實裝以下防禦聯鎖：

* **聯鎖路徑安全檢測 (Traversal Protection)**：
  當聯鎖驗證工具（如 `validate_output.py`）需要讀取 `vis_2_dis` 專案中的 `validate_renderer_skin_asset.py` 驗證器時，必須先執行安全路徑比對，確保外部引用的路徑完全合法，防範路徑跨越漏洞。
* **環境變數強制隔離 (Environment Isolation)**：
  在調用任何外部工具或 subprocess 執行自檢時，一律將 Python 的寫入快取禁用：
  `os.environ["PYTHONDONTWRITEBYTECODE"] = "1"`
  杜絕因執行測試而在外部專案或唯讀專案目錄中自動生成 `__pycache__/` 緩存資料夾，維護物理文件系統的絕對純淨。
* **二進位防漏聯鎖 (Binary Mute Lock)**：
  本專案產出物僅限為靜態 JSON 契約（如 `manifest.json`）文字，任何情況下，**本專案之腳本、範例與 tests 絕不生成、複製或推動任何二進位大數據包（如 *.npz）**，確保 Git 倉庫快照維持輕量化與純粹文檔性質。
