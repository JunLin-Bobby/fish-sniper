import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import { afterEach, test } from 'node:test'
import { setTimeout as delay } from 'node:timers/promises'
import {
  deleteResource, getJson, HttpStatusError, NetworkRequestError, patchJson, postForm,
  postJson, RequestAbortedError, RequestTimeoutError, requestTimeouts,
} from '../src/api/http.ts'
import { isDefinitiveSubmissionError } from '../src/catch-logs/lib/submissionOutcome.ts'
import { createCatchLogWithPhotos } from '../src/catch-logs/api/catchLogApi.ts'

const originalFetch = globalThis.fetch
Object.defineProperty(globalThis, 'window', {
  configurable: true, value: { localStorage: { getItem: () => 'deadline-test-token' } },
})

// 每個測試還原 fetch，不讓模擬網路影響其他測試。
afterEach(() => { globalThis.fetch = originalFetch })

// 本機 HTTP server 刻意不回應／回半份 body，驗證原生 fetch 而非只靠 mock Promise。
async function withServer(handler: (request: IncomingMessage, response: ServerResponse) => void, run: (url: string) => Promise<void>): Promise<void> {
  const server = createServer(handler)
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  assert.ok(address && typeof address !== 'string')
  try { await run(`http://127.0.0.1:${address.port}`) }
  finally { server.closeAllConnections(); await new Promise<void>((resolve) => server.close(() => resolve())) }
}

// 沒有成功、HTTP 錯誤或任何 headers 的情況，也必須能從 await 退出。
test('a server that never responds produces a client timeout, not a fake HTTP status', async () => {
  await withServer(() => {}, async (apiBaseUrl) => {
    await assert.rejects(getJson({ apiBaseUrl, path: '/', timeoutMs: 50 }), (error: unknown) => {
      assert.ok(error instanceof RequestTimeoutError)
      assert.equal(error.timeoutMs, 50)
      assert.equal(error instanceof HttpStatusError, false)
      return true
    })
  })
})

// 收到 headers 不代表讀取完成；期限必須保留到串流 body 讀完。
test('deadline remains active after headers while response body stalls', async () => {
  await withServer((_request, response) => {
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.flushHeaders()
    response.write('{"saved":')
  }, async (apiBaseUrl) => {
    await assert.rejects(getJson({ apiBaseUrl, path: '/', timeoutMs: 80 }), RequestTimeoutError)
  })
})

// 主動離開頁面不可被標成 timeout；原來的 caller signal 必須仍有作用。
test('caller cancellation aborts the combined request without misclassifying timeout', async () => {
  const caller = new AbortController()
  await withServer(() => caller.abort(), async (apiBaseUrl) => {
    await assert.rejects(getJson({ apiBaseUrl, path: '/', signal: caller.signal, timeoutMs: 1000 }), RequestAbortedError)
  })
})

// 已取消的請求不應送出，且不受 caller 自訂的 abort reason 型別影響。
test('already aborted caller does not dispatch fetch', async () => {
  const caller = new AbortController()
  caller.abort('navigation')
  let called = false
  globalThis.fetch = async () => { called = true; return Response.json({}) }
  await assert.rejects(getJson({ apiBaseUrl: 'http://test', path: '/', signal: caller.signal }), RequestAbortedError)
  assert.equal(called, false)
})

// 瀏覽器傳輸 TypeError 和伺服器真的回 HTTP 503 是不同錯誤。
test('network failure preserves its cause and does not invent an HTTP response', async () => {
  const cause = new TypeError('connection unavailable')
  globalThis.fetch = async () => { throw cause }
  await assert.rejects(getJson({ apiBaseUrl: 'http://test', path: '/' }), (error: unknown) => {
    assert.ok(error instanceof NetworkRequestError)
    assert.equal(error.cause, cause)
    return true
  })
  globalThis.fetch = async () => Response.json({ detail: 'unavailable' }, { status: 503 })
  await assert.rejects(getJson({ apiBaseUrl: 'http://test', path: '/' }), HttpStatusError)
})

// JSON 解析錯誤不是斷線，也不能被新錯誤分類吞掉。
test('invalid JSON remains a parse error', async () => {
  globalThis.fetch = async () => new Response('invalid', { status: 200 })
  await assert.rejects(getJson({ apiBaseUrl: 'http://test', path: '/' }), SyntaxError)
})

// 成功後必須清除 timer 和 caller listener，避免稍後誤取消或累積監聽器。
test('success clears timeout and unregisters the caller signal listener', async () => {
  const caller = new AbortController()
  let signal: AbortSignal | null = null
  let removed = 0
  const originalRemove = caller.signal.removeEventListener.bind(caller.signal)
  caller.signal.removeEventListener = (...args) => { removed++; originalRemove(...args) }
  globalThis.fetch = async (_url, options) => { signal = options!.signal!; return Response.json({ ok: true }) }
  assert.deepEqual(await getJson({ apiBaseUrl: 'http://test', path: '/', signal: caller.signal, timeoutMs: 20 }), { ok: true })
  await delay(35)
  assert.equal(signal!.aborted, false)
  assert.equal(removed, 1)
})

// 只設定一個共用 helper，讓 GET／POST／multipart／PATCH／DELETE 都有期限。
test('all HTTP methods enforce the same configurable deadline', async () => {
  const operations = [
    () => getJson({ apiBaseUrl: 'http://test', path: '/', timeoutMs: 5 }),
    () => postJson({ apiBaseUrl: 'http://test', path: '/', body: {}, timeoutMs: 5 }),
    () => postForm({ apiBaseUrl: 'http://test', path: '/', body: new FormData(), timeoutMs: 5 }),
    () => patchJson({ apiBaseUrl: 'http://test', path: '/', body: {}, timeoutMs: 5 }),
    () => deleteResource({ apiBaseUrl: 'http://test', path: '/', timeoutMs: 5 }),
  ]
  globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {
    options!.signal!.addEventListener('abort', () => reject(options!.signal!.reason), { once: true })
  })
  for (const operation of operations) await assert.rejects(operation(), RequestTimeoutError)
})

// 正式提交期限為 60 秒；測試只縮短計時，不改變真實錯誤與恢復判斷。
test('photo submission waits at most 60 seconds and preserves an unconfirmed outcome', async (context) => {
  const originalSetTimeout = globalThis.setTimeout
  let deadline: number | undefined
  context.mock.method(globalThis, 'setTimeout', (callback: () => void, milliseconds?: number) => {
    deadline = milliseconds
    return originalSetTimeout(callback, 5)
  })
  globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {
    options!.signal!.addEventListener('abort', () => reject(options!.signal!.reason), { once: true })
  })
  await assert.rejects(createCatchLogWithPhotos('http://test', {
    species_name: 'Bass', caught_at: '2026-10-26T12:00:00Z',
    length_cm: null, weight_g: null, fishing_method: null, notes: null,
  }, [], 'test-submission'), (error: unknown) => {
    assert.ok(error instanceof RequestTimeoutError)
    assert.equal(error.timeoutMs, 60_000)
    assert.equal(isDefinitiveSubmissionError(error), false)
    return true
  })
  assert.equal(deadline, 60_000)
})

// 明確記錄不同工作期限，並驗證逾時與斷線不能清除原提交。
test('request profiles and submission reset policy preserve ambiguous outcomes', () => {
  assert.deepEqual(requestTimeouts, { default: 15000, submission: 60000, receipt: 10000 })
  for (const error of [new RequestTimeoutError(10), new NetworkRequestError(null), new RequestAbortedError(),
    new HttpStatusError(408, ''), new HttpStatusError(504, ''), new HttpStatusError(503, '')]) {
    assert.equal(isDefinitiveSubmissionError(error), false)
  }
  assert.equal(isDefinitiveSubmissionError(new HttpStatusError(422, '')), true)
  for (const code of ['submission_pending', 'submission_conflict']) {
    assert.equal(isDefinitiveSubmissionError(new HttpStatusError(409, JSON.stringify({ detail: { code } }))), false)
  }
  for (const code of ['submission_failed', 'submission_deleted']) {
    assert.equal(isDefinitiveSubmissionError(new HttpStatusError(409, JSON.stringify({ detail: { code } }))), true)
  }
  assert.equal(isDefinitiveSubmissionError(new HttpStatusError(409, 'bad gateway')), false)
})
