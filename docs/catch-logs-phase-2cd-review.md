# Catch Log 2C／2D：實作與 code review 導覽

## 先用自然語言理解這次功能

新增魚獲時，魚種、時間、釣法、備註與最多兩張照片在同一張表單，按一次儲存。
照片選填，接受 JPEG、PNG、HEIC，每張上限 20 MiB、60 百萬像素。
後端先驗證所有內容，再建立不公開的內部草稿。只有全部照片上傳完成，
資料庫才用一筆 transaction 將整筆魚獲與照片發布為 ready。

這不是 Storage 與 PostgreSQL 的分散式交易。失敗時先取消發布資格，再嘗試刪除
Storage 物件；清理失敗保留路徑與狀態，以便背景恢復或手動指令重試。
發布成功但 HTTP 回應遺失時，重送同一提交識別碼會取得原紀錄，不能誤刪照片。

照片會校正方向、縮到長邊最多 2048 px、轉為 JPEG，透明背景轉白色。
原檔不保留，展示圖片不含 EXIF/XMP。擷取到的最小必要時間／GPS 是私人候選資訊，
不自動覆蓋釣獲時間，也不直接建立釣點。缺少時區的照片時間只能提示，不直接套用。

目前「新增」可附照片；既有紀錄的編輯仍只修改文字欄位，相簿可查看及刪除照片。
既有紀錄新增／替換照片、地圖確認釣點與 HEIC 原檔下載不在本版範圍。

## 閱讀順序一：從前端按下儲存開始

1. `frontend/src/catch-logs/components/CatchLogForm.tsx` 的 `submit()`：
   驗證魚種、時間與數值，將裝置本地時間轉 ISO，呼叫 `onSubmit(input, files)`。
   `CatchPhotoPicker` 是這張表單的子元件，自己不送上傳請求。
2. `CatchLogsWorkspace.tsx` 的 `save()`：防止連點，新增時呼叫提交 hook；成功才開詳情。
3. `hooks/useCatchLogSubmission.ts` 的 `submit()` 只管理 UUID 與狀態，不保存文字／File 快照。
   正常 POST 不輪詢，失聯才自動恢復；只將按帳號區分的 UUID 存入 localStorage。
   確定失敗清空表單與檔案選取，不重傳原照片、不要求使用者手動確認。
   詳細閱讀順序與新期限規則見 [上傳恢復 review](catch-log-upload-recovery.md)。
4. `api/catchLogApi.ts` 的 `createCatchLogWithPhotos()`：建立 FormData，放入
   `payload` JSON 字串、`submission_id` 與重複的 `photos` 檔案欄位。
5. `frontend/src/api/http.ts` 的 `postForm()`：加 Bearer token，但不手動指定
   Content-Type，讓瀏覽器產生 multipart boundary；header 另帶相同 Idempotency-Key。

傳輸是一個 `POST /api/v1/catch-logs/with-photos`。既有 JSON 建立與 PATCH API 保留。

## 閱讀順序二：需求如何對應後端 function

### 0. 先驗證所有欄位、照片

`router.py:create_catch_log_with_photos()` 透過 `CurrentUserDependency` 驗證 JWT，
用 `CatchLogCreate.model_validate_json()` 驗證白名單欄位與時區，限制 multipart 張數／欄位。
`upload_limits.py:CatchUploadLimitMiddleware` 在解析前限制實際 body bytes，包含 chunked body。

接著進入 `service.py:CatchLogService.create_with_photos()`：

```python
prepared, hashes = await photos_service.validate_and_prepare(files)
```

`photo_service.py:validate_and_prepare()` 有界讀取每張原檔，呼叫 worker thread 執行
`photo_processing.py:prepare_photo()`，檢查實際解碼格式、bytes、像素及單張圖片。
副檔名與 Content-Type 不作為可信格式依據。任一張無效，還不會建立草稿。

`photo_metadata.py:extract_photo_metadata()` 在輸出圖片去除 EXIF 前讀取候選資訊。
沒有 EXIF、沒有 GPS 或無效的拍攝欄位，不會讓有效圖片上傳失敗。

### 1. 建立內部待完成紀錄，暫不出現在正常列表

同一個協調 function 接著執行：

```python
manifest = photos_service.build_manifest(user_id, log_id, prepared)
claim = await self._repository.begin_submission(
    user_id, submission_id, fingerprint, log_id, values, manifest,
)
```

`build_manifest()` 先安排唯一 Storage 路徑。
`supabase_repository.py:begin_submission()` 呼叫 SQL `begin_catch_submission()`。
SQL 在一筆交易內建立 pending 魚獲、所有照片 manifest 與提交收據。
同一 user／submission 由 advisory transaction lock 序列化，不依賴 Python 記憶體鎖。
相同識別碼內容不同會衝突，已成功的相同提交直接回原紀錄。

`SupabaseCatchLogsRepository._owned_params()` 與 `list_for_user()` 都帶
`status=eq.ready`；未完成／清理中的紀錄不能透過一般 GET、列表或 PATCH 操作。
讀寫也同時限定 user_id，知道別人的 log UUID 仍不能操作。

### 2. 上傳全部照片

```python
await photos_service.upload_all(user_id, log_id, prepared, manifest)
```

`photo_service.py:upload_all()` 逐張呼叫共用 `SupabaseStorageClient.upload()`。
每張成功後透過 `SupabaseCatchPhotoRepository.mark_uploaded()` 標記 uploaded。
SQL 再次持鎖確認父紀錄仍是 pending；uploaded 還不是可對使用者顯示的 ready。

### 3. 在資料庫交易中將魚獲與照片一起發布

```python
return await self._repository.publish_submission(user_id, log_id)
```

真正 transaction 位於 migration 的 `publish_catch_submission()`，不是 Python 的 try：

```sql
-- 先持鎖驗證 owner、pending，以及所有照片都已 uploaded。
update public.catch_log_photos set status = 'ready' where catch_log_id = p_log_id;
update public.catch_logs set status = 'ready' where id = p_log_id returning * into record;
update public.catch_log_submissions set status = 'ready'
    where user_id = p_user_id and log_id = p_log_id;
```

以上三個更新在同一次 RPC 的 PostgreSQL transaction 裡。
中途任一 SQL statement 失敗，三者一起 rollback。Storage 本身不參加這筆 transaction。

### 4. 任一步失敗，不發布魚獲，嘗試清理

`create_with_photos()` 捕捉資料庫／Storage 失敗，呼叫
`_compensate_failed_submission()`：

```python
if await self._repository.claim_cleanup(user_id, log_id):
    await self._photos.cleanup_files(log_id)
    await self._repository.finish_cleanup(user_id, log_id)
```

`claim_catch_cleanup()` 先將 pending 取消成 cleanup_pending，禁止它再發布或標記上傳。
若紀錄其實已 ready（例如 COMMIT 成功但回應遺失），不會授予補償清理權。
因此不會在網路故障時誤刪已發布照片。

`cleanup_files()` 依 manifest 刪所有安排過的路徑，包含未收到成功回應的上傳。
為了容納 timeout 後可能晚到的上傳，已取消草稿的 manifest 至少保留五分鐘，
再做第二次清理；這不是對無限期遠端延遲的原子保證。

### 5. 清理失敗，保留待清理狀態供重試

`service.py:recover_pending()` 讀取 DB 中的隱藏紀錄，重新取得清理權，再執行刪檔與
`finish_cleanup()`。新版先呼叫 `expire_submissions()`，依資料庫 deadline 結束過期操作；
沒有 catch row 的早期登記也會收尾。不再以一小時作為一般提交完成期限。

`recovery.py:retry_cleanup()` 於 app 執行期間每 60 秒重試，工作資料不存記憶體。
`catch_cleanup_lifespan()` 在 app 停止時取消計時器。多個 worker 的操作仍受 DB 狀態保護。
若停機，工作會留在 DB，下次啟動後繼續；也可手動：

```bash
docker compose -f docker-compose-dev.yaml exec backend uv run python -m app.catch_logs.cleanup
```

指令回傳 cleaned／retained／errors 計數，errors 非零時結束碼為 1。
可設定 `CATCH_CLEANUP_INTERVAL_SECONDS=0` 關閉自動恢復，保留手動指令。

## 閱讀順序三：儲存後的照片與 EXIF

`useCatchPhotos()` → `fetchCatchPhotos()` → `GET /{log_id}/photos` →
`CatchLogService.list_photos()` 檢查 owner → `CatchPhotoService.list_ready()` → 短效連結。
signed URL 不寫 DB，前端在到期前重讀；拿到網址的人在有效期內仍可存取，不能視為公開網址。

`CatchPhotoGallery` 顯示照片、展開與單張刪除。
`PhotoMetadataSuggestion` 只在照片有含時區的時間時提供套用按鈕，按下後使用既有 PATCH。
GPS 只提示存在，沒有 AI 推測，也沒有手動經緯度輸入框或已確認釣點。

刪整筆魚獲由 `CatchLogService.delete_for_user()` 先記錄 deleting 意圖、清除檔案再移除
資料列。單張由 `CatchPhotoService.delete_photo()` 管理，失敗保留 deleting 供恢復重試。
SQL cascade 本身不會刪除 Storage 檔案；未來若做「刪除帳號」也必須整合檔案清理。

## 設定、migration 與驗證

新增 migration：`supabase/migrations/202610220001_catch_log_photos.sql`。
需在既有 users、catch_logs migration 之後執行。它會建立 private `catch-photos` bucket
（一般 PostgreSQL 測試沒有 Storage schema 時跳過），明確給 service_role table／RPC 權限，
不授權 anon／authenticated。FishSniper JWT 仍由後端驗證，不直接當 Supabase Auth JWT。

本次不自動套用 hosted Supabase migration，也不使用正式照片測試。
套用 migration 後重啟／更新 Docker 依賴，新增 Pillow、pillow-heif、python-multipart。
背景清理在 schema 尚未套用時只會記錄安全錯誤，不應讓 health endpoint 故障。

測試包含：實際 HEIC 解碼、去 EXIF、檔案／像素／張數限制、跨帳號隔離、零張照片、
第二張上傳失敗、發布失敗、清理失敗重跑、遺失發布回應、提交去重、chunked 超限。
`supabase/tests/catch_log_photos.sql` 以真正 PostgreSQL 驗證權限、鎖定狀態、交易回滾與恢復。
前端測試驗證 FormData、Bearer、照片限制與跨帳號收據隔離。

瀏覽器驗證使用真實前端及 mock API，不等於已驗證正式 Supabase Storage 的連線與憑證。
仍需在套用 migration 後，以自己的帳號做一次真實上傳／讀取／刪除 smoke test。

## 舊版網路等待設計（歷史紀錄，已被取代）

以下為重構前的紀錄，不是目前行為。現行設計請讀
[上傳恢復 review](catch-log-upload-recovery.md)：60 秒傳輸、後端期限、自動恢復，
已移除原快照、15 秒硬中止及手動確認入口。

先看 `frontend/src/api/http.ts` 的 `requestJson()`：現在所有共用 HTTP 方法都有等待期限。
一般請求與魚獲含照片提交皆為 15 秒、確認收據 10 秒，定義於 `requestTimeouts`。
各 helper 亦可接收 `timeoutMs` 與呼叫端的 `signal`。
2026-10-26 將提交期限從 180 秒縮短至 15 秒，避免使用者長時間卡在儲存中。
照片原檔合計最多約 40 MiB，慢速網路可能在上傳完成前就逾時；15 秒是前端等待期限，
不是已量測的常態完成時間或伺服器 SLA。圖片目前在後端才縮小，不會減少前端原檔上傳量。

這不是只顯示一個逾時 toast：`AbortController` 真正取消這次瀏覽器傳輸。
期限直到 `await parseJsonResponse()` 完成才清除，因此涵蓋 HTTP headers 到達後卡住的 body。
finally 會清除 timer 與 caller signal 的監聽，不留下完成後才觸發的取消。
計時仍受瀏覽器排程／背景分頁影響，不能當成精準的硬即時期限。

錯誤分類：

- `HttpStatusError`：收到並讀取 HTTP 非成功回應。
- `RequestTimeoutError`：前端等待期限到了，不假造 HTTP 408／504。
- `NetworkRequestError`：fetch／讀取 body 的傳輸 TypeError，可能是斷線、DNS 或 CORS；
  不直接斷定使用者離線，保留 cause 供除錯。
- `RequestAbortedError`：呼叫端主動取消；原有讀取 hook 仍會忽略已卸載的結果。
- 無效 JSON 仍保留原本的解析錯誤，不誤分類成網路中斷。

接著看 `useCatchLogSubmission.submit()` 與 `lib/submissionOutcome.ts` 的
`isDefinitiveSubmissionError()`：timeout／network／取消等待都不能證明資料庫 rollback，
因此不會 clear 原快照與收據，而是進入 uncertain。
`CatchLogsWorkspace.save()` 的 finally 會解鎖畫面，並顯示「尚未確認是否儲存成功」。
不會在背景自動重送建立請求；使用者確認結果或手動重試時仍沿用同一識別碼。

`check()` 現在回傳可呈現的 `checkResult`：pending、notFound、failed、deleted、timeout、
network、error。查詢失敗保留原收據、解除 checking，401 交回登入流程。
notFound 不證明失敗，failed 代表提交已取消、不會發布，但檔案清理可能還在進行。
舊查詢在開始提交或卸載時會取消，避免晚到的查詢清掉正在重試的資料。

`CatchPhotoGallery` 的修改／刪除逾時也改用「可能已完成，請重讀確認」提示。
中英文文案放在 i18n，不把錯誤 class 的英文訊息直接當作產品提示。

後端本次保留原有 HTTPX 連線／讀寫等待限制，沒有加入強制終止整筆魚獲流程的 deadline。
`db/client.py` 與 `storage/client.py` 分開記錄 provider、timeout／network／http 類型，
timeout 再記 ConnectTimeout／ReadTimeout／WriteTimeout／PoolTimeout；不記錄 URL、
Bearer、secret、照片路徑或上游原始錯誤內容。timeout 仍會轉成既有安全例外，沿用補償流程。
瀏覽器 abort 不代表後端停止；提交去重、查詢收據及持久清理仍不可移除。

新增驗證：`frontend/tests/httpDeadline.test.ts` 用真正本機 HTTP server 測不回應和半份 body，
並測試 caller 取消、timer／listener 清除、錯誤分類與收據保留規則。
`backend/tests/api/test_upstream_timeouts.py` 驗證上游 timeout 分類與 log 不洩漏資料。
隔離瀏覽器測試縮短測試頁面的計時器，驗證結果查詢各狀態及逾時後手動重試使用原快照；
另以縮短測試計時器的 API 測試驗證含照片提交使用正式的 15 秒設定，逾時仍保留原提交。
目前正式程式為 15／15／10 秒。本次不需額外資料庫 migration。
