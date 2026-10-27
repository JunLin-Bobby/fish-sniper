# 魚獲上傳異常恢復（2026-10-26）

這份文件取代先前「15 秒硬中止、保存原快照、使用者手動確認」的設計。
沒有持久草稿、重傳快照、離線佇列或背景建立魚獲工作。正常 POST 自行完成，不輪詢。

## Code review：從使用者按儲存開始

1. `CatchLogForm.submit()` 驗證欄位，組出文字與選取檔案。這是表單／傳輸必需的暫時資料。
2. `CatchLogsWorkspace.save()` 新增時委派共用的 `useCatchLogSubmission.submit()`。
3. 此 hook 放在 `DashboardPage`，不依賴表單掛載；只保留 UUID、controller、狀態及計時資訊，
   沒有 `input` 或 `File[]` ref。正常 POST 期間，online/focus 事件不會另啟動查詢。
4. `createCatchLogWithPhotos()` 把同一 UUID 放入 `Idempotency-Key` header 與 multipart 欄位。
   `http.postForm()` 自動附 Bearer，不手動指定 Content-Type；整次傳輸期限為 60 秒。
5. `router.create_catch_log_with_photos()` 先驗證 JWT 與 header UUID，再呼叫
   `service.register_submission()`，最後才讀 multipart。接收上限預設 45 秒。
6. 完整收件後，`start_processing()` 用 DB clock 設定新的 30 秒處理期限；
   Python `asyncio.timeout` 限制等待，DB 的期限／狀態則防止晚到工作發布。
7. `create_with_photos()` 沿用原圖片驗證／轉檔、manifest、Storage 上傳與原子發布。
   server-only attempt UUID 防止另一個重複 POST 接管正在處理的登記。
8. 成功直接回 201。錯誤先呼叫 `fail_attempt()`；若實際已 COMMIT，保留成功、不刪照片。
   驗證失敗也留下最小失敗收據，但沒有魚獲／照片半成品。multipart 檔案會關閉。
9. 前端成功或確定失敗才清識別碼；revision 讓新增表單重新掛載，清掉欄位與檔案引用。
   編輯／刪除的原流程不混入這次建立操作狀態。

## 只有失聯才進行恢復

`submissionRecovery.recoverSubmission()` 不接收文字／照片，不能發出建立 API：

- 呼叫 `POST /submissions/{id}/resolve`。它可能終結操作，因此不是有寫入副作用的 GET。
- 每輪最多三次、每次最多十秒、連同間隔最多三十秒；最後一次依剩餘預算縮短。
- 傳輸失敗等 2 秒、再失敗等 5 秒；pending 等後端給的時間，不固定每兩秒查。
- 若明確的後端 deadline 超出本輪預算，只安排一次 deadline 喚醒，不能永久停在
  「其實後端已結束、但前端再也沒有事件」的狀態。這不是常態或無限輪詢。
- 仍無法取得結果就停本輪。恢復網路／回到 App 可再觸發，active controller 防止並行，
  focus/storage 事件另有三十秒冷卻。真正 online 可立即開始一輪。
- 401 交回登入流程，不刪識別碼。卸載／換帳號取消請求及 timer，世代與 owner 檢查
  防止晚到的舊回應更新新帳號。StrictMode 測試掛載不重複發送啟動恢復。
- 共用 header 只顯示儲存中或最終成功／失敗，沒有確認按鈕／內部狀態字串。

`submissionStorage` 只持久保存按帳號區分的 UUID，且只清除期望的舊 ID，不覆蓋另一分頁
較新寫入的 ID。舊 sessionStorage 收據會遷移。localStorage 被禁止／清除時不保證跨重開恢復。
沒有原照片時只確認結果，絕不假裝能重新上傳。持續斷線無法可靠斷定成功或失敗。

## DB 交易與恢復責任

新 migration：`202610260001_submission_recovery.sql`。

- `register_catch_submission()`：先保留識別碼、server attempt 與接收 deadline。
- `start_catch_processing()`：只有擁有 attempt 能在未過期時切換處理期限。
- `begin_catch_submission()`：附加 fingerprint 與 manifest，不能復活終結收據。
- `publish_catch_submission()`：提交成功前檢查期限、父子狀態；同筆交易一起 ready。
- `resolve_catch_submission()`：未知 ID 寫失敗 tombstone；過期操作失敗並留下清理 manifest；
  已成功永遠回成功；尚在期限內回 pending 與 `retry_after_ms`。
- `fail_catch_submission()`：只允許擁有 attempt 終結未完成操作，不動已成功提交。
- `expire_catch_submissions()`：由既有恢復 worker 掃描，沒有 catch row 的登記也能收尾。

所有涉及收據／父紀錄的發布、終結與清理使用同一 advisory lock 順序，再鎖資料列，
避免發布與終結各持一邊鎖造成死鎖。Storage 不在 DB transaction 內；保留原五分鐘寬限與
第二輪檔案清理。已套用 migration 不回寫；新 RPC 明確只授權 service_role。
底層服務停止時不能保證準點清理；恢復後及下次 resolve 都能結束過期 pending。

## 部署與驗證

1. 在既有三份 migration 之後套用新 migration。不要只更新後端而漏掉 DB functions。
2. 更新前後端；header UUID 與 body UUID 必須一致。舊 backend-only SQL 六參數呼叫
   保留相容，但舊瀏覽器沒有 header 的 multipart 請求必須重新載入新版。
3. `.env.example` 提供 `CATCH_UPLOAD_RECEIVE_SECONDS=45`、
   `CATCH_UPLOAD_PROCESSING_SECONDS=30`；這些是可量測調整的保護值，不是 SLA。
4. 跑 Python／前端測試及建置，並在隔離 PostgreSQL 執行 `supabase/tests/*.sql`。
5. 用真正 Supabase 做一次新增／讀取／刪除 smoke test。開發測試不會套用 hosted migration。

本次驗證包含 API 正常／失敗／處理與收件逾時、墓碑與晚到請求、跨帳號恢復、孤兒登記，
前端有限重試／三十秒預算／取消，及瀏覽器正常不查詢、失敗清空、不自動重傳、
回應遺失找回、重新開啟、401、320／390／1280px。瀏覽器 API mock 不代表正式 Storage 已驗證。
