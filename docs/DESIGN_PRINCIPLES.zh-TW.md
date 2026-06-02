# 設計哲學與原則 (Design Principles)

> [!IMPORTANT]
> **專案治理與非生產聲明：**
> * **非生產環境就緒 (Not production-ready)**：本實驗專案產出之代碼與工具僅作為外部原型參考（external reference prototype），絕非生產就緒代碼。
> * **未授權合併產品 Repo (Not authorized for product repo integration)**：嚴禁將本專案的任何編譯或工具代碼併入三大產品倉庫中，主線倉庫維持唯讀。
> * **需要 O_1 審查 (Requires o_1 review before product adoption)**：本專案之機制若要被產品主線採用，必須經過 `o_1` 進行嚴格審查與正式授權。

本文件定義 `rrkal-contract-islands`（全域契約語法糖實驗室）的核心設計哲學與實作原則，作為跨 Agent 協作開發與代碼審閱時的最高指導綱領。

---

## 1. 契約語法糖定位 (Declarative Contract Sugar Only)

本實驗室的根本使命是 **「讓契約手寫更舒服、閱讀更清晰，但絕不創造執行期新真相」**。

* **聲明式優先 (Declarative Over Imperative)**：
  島嶼語法糖 (.island) 僅包含結構、配置、欄位與關聯宣告，**絕對不包含任何命令式或具備執行期副作用 (Side-effects) 的程式碼邏輯**。
* **靜態投影 (Static Projection)**：
  編譯器唯一的職責是將聲明式語法糖進行語意分析與結構扁平化，投影輸出為標準的 JSON（如 `manifest.json`）。產品專案只需在載入時消費此靜態 JSON 檔案，不需要（也絕不允許）在執行期動態解析島嶼語法糖。
* **低依賴高内聚**：
  保持本專案的 100% 獨立性，絕不向外引入複雜的第三方依賴，亦不向產品專案滲透任何模組，維持系統最低限度的耦合。

---

## 2. 安全防範與零漏洞設計原則 (Zero-Vulnerability Architecture)

由於語法糖解析器涉及文字結構處理，安全是我們不可動搖的第一防禦線：

* **100% 物理杜絕 Dynamic Evaluation**：
  任何情況下，**嚴禁在解析器與編譯器中使用 Python 內建的 `eval()`、`exec()`、`__import__()`、`getattr()` 或 `globals()` 等具備動態程式執行能力的危險語法**。
* **手寫 Tokenizer 與 Parser (Zero-dependency Parser)**：
  不依賴複雜的第三方解析框架（如 PLY、Lark 等），完全使用內建 `re` 庫手寫詞法 Token 掃描器與 Recursive Descent 遞迴下降解析器。這使得整個解析邏輯 100% 可視、可控且便於安全審查。
* **硬性限制防禦 (Hard Limits Protection)**：
  在詞法掃描前，先校驗輸入的 `.skinisland` 實體檔案大小與字元長度限制，防範藉由惡意構造巨大文字檔發起的 Memory Bomb 與 CPU 耗竭攻擊。
* **安全沙盒隔離 (Sanitized Parser)**：
  解析器在遇到任何未知、非法或不合規的字元 / tokens 時，應立即中斷解析並精準拋出 `SyntaxError`（指明錯誤行號與字元位置），決不嘗試進行模糊猜測或容忍後門代碼。
