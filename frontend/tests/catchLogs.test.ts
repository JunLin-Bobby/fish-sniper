import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { HttpStatusError } from '../src/api/http.ts'
import { createCatchLog, deleteCatchLog, fetchCatchLog, fetchCatchLogs, updateCatchLog } from '../src/catch-logs/api/catchLogApi.ts'
import type { CatchLogInput } from '../src/catch-logs/api/catchLogTypes.ts'
import { formatCaughtAt, toLocalDateTimeInput } from '../src/catch-logs/lib/catchLogPresentation.ts'

const originalFetch = globalThis.fetch
const input: CatchLogInput = {
  species_name: '大口黑鱸', caught_at: '2026-10-20T07:30:00+08:00',
  length_cm: null, weight_g: null, fishing_method: 'fly_fishing', notes: null,
}
Object.defineProperty(globalThis, 'window', {
  value: { localStorage: { getItem: () => 'test-fishsniper-token' } }, configurable: true,
})

// 每個測試結束還原 fetch，避免 mock 影響其他 HTTP 驗證。
afterEach(() => { globalThis.fetch = originalFetch })

// 驗證真實 API helper 發出正確 URL、JSON 與 Bearer header，而非只測試型別。
test('create uses JSON data and never sends an owner', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://test/api/v1/catch-logs')
    assert.equal(options?.method, 'POST')
    const headers = new Headers(options?.headers)
    assert.equal(headers.get('Authorization'), 'Bearer test-fishsniper-token')
    assert.equal(headers.get('Content-Type'), 'application/json')
    assert.deepEqual(JSON.parse(options?.body as string), input)
    return Response.json({ id: 'new', ...input }, { status: 201 })
  }
  assert.equal((await createCatchLog('http://test', input)).id, 'new')
})

// PATCH 的 null 必須保留，否則使用者無法清空原本填過的尺寸或備註。
test('update preserves optional nulls and uses PATCH', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://test/api/v1/catch-logs/log-id')
    assert.equal(options?.method, 'PATCH')
    assert.equal(JSON.parse(options?.body as string).length_cm, null)
    return Response.json({ id: 'log-id', ...input })
  }
  await updateCatchLog('http://test', 'log-id', input)
})

// 刪除成功的 204 沒有 JSON，不能因解析空字串而誤報刪除失敗。
test('delete accepts empty 204 and keeps authentication', async () => {
  globalThis.fetch = async (_url, options) => {
    assert.equal(options?.method, 'DELETE')
    assert.equal(new Headers(options?.headers).get('Authorization'), 'Bearer test-fishsniper-token')
    return new Response(null, { status: 204 })
  }
  assert.equal(await deleteCatchLog('http://test', 'log-id'), undefined)
})

// 非 204 的 JSON API 若回傳空 body，應報錯，不能把無效回應當成新增成功。
test('empty JSON success is not treated as a valid created record', async () => {
  globalThis.fetch = async () => new Response('', { status: 201 })
  await assert.rejects(createCatchLog('http://test', input), SyntaxError)
})

// 列表必須傳分頁參數與 AbortSignal，並保留有下一頁的資訊。
test('list sends bounded pagination and cancellation', async () => {
  const controller = new AbortController()
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://test/api/v1/catch-logs?limit=10&offset=10')
    assert.equal(options?.signal, controller.signal)
    return Response.json({ items: [], limit: 10, offset: 10, has_more: false })
  }
  assert.equal((await fetchCatchLogs('http://test', 10, controller.signal)).offset, 10)
})

// 詳情需使用獨立 GET，不將列表快照誤當成後端驗證後的最新紀錄。
test('detail requests one encoded resource', async () => {
  globalThis.fetch = async (url) => {
    assert.equal(url, 'http://test/api/v1/catch-logs/log%2Fid')
    return Response.json({ id: 'log/id', ...input })
  }
  assert.equal((await fetchCatchLog('http://test', 'log/id')).id, 'log/id')
})

// 保留 401、404、422、503 狀態碼，讓 UI 區分登出、找不到、驗證失敗與暫時故障。
for (const status of [401, 404, 422, 503]) {
  // 每種失敗均不回傳假的成功結果，並保留共用錯誤型別。
  test(`HTTP ${status} remains an HttpStatusError`, async () => {
    globalThis.fetch = async () => Response.json({ detail: 'test error' }, { status })
    await assert.rejects(deleteCatchLog('http://test', 'id'), (error: unknown) => {
      assert.ok(error instanceof HttpStatusError)
      assert.equal(error.status, status)
      return true
    })
  })
}

// 本地 datetime-local 值應可轉回同一時間點，不因固定台灣時區造成八小時偏移。
test('local date input round trips the original instant', () => {
  const instant = '2026-10-20T07:30:15+08:00'
  assert.equal(new Date(toLocalDateTimeInput(instant)).toISOString(), new Date(instant).toISOString())
  assert.match(formatCaughtAt(instant, 'en'), /2026/)
  assert.match(formatCaughtAt(instant, 'zh-TW'), /2026/)
})
