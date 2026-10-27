import assert from 'node:assert/strict'
import { test } from 'node:test'
import { HttpStatusError, NetworkRequestError, RequestTimeoutError } from '../src/api/http.ts'
import { recoverSubmission, waitForRecovery } from '../src/catch-logs/lib/submissionRecovery.ts'

// 立即取得終局只送一次請求，不進入任何持續輪詢。
test('recovery finishes immediately on ready or failed', async () => {
  for (const status of ['ready', 'failed'] as const) {
    let calls = 0
    const result = await recoverSubmission({ signal: new AbortController().signal,
      resolve: async () => { calls++; return { status, log_id: 'log', retry_after_ms: 0 } },
      wait: async () => { assert.fail('terminal result must not wait') },
    })
    assert.equal(result?.status, status)
    assert.equal(calls, 1)
  }
})

// 傳輸錯誤採 2／5 秒退避，最多三次，完全不重送建立資料。
test('network errors stop at three attempts with exact backoff', async () => {
  let calls = 0
  let clock = 0
  const waits: number[] = []
  const result = await recoverSubmission({ signal: new AbortController().signal,
    now: () => clock,
    wait: async (ms) => { waits.push(ms); clock += ms },
    resolve: async (_signal, timeoutMs) => { calls++; assert.equal(timeoutMs, 10_000); throw new NetworkRequestError(null) },
  })
  assert.equal(result, null)
  assert.equal(calls, 3)
  assert.deepEqual(waits, [2000, 5000])
})

// 總預算包含每次請求與等待，第三次只剩三秒，不會再額外等十秒。
test('the thirty second budget includes timeouts and backoff', async () => {
  let clock = 0
  const limits: number[] = []
  await recoverSubmission({ signal: new AbortController().signal, now: () => clock,
    wait: async (ms) => { clock += ms },
    resolve: async (_signal, ms) => { limits.push(ms); clock += ms; throw new RequestTimeoutError(ms) },
  })
  assert.deepEqual(limits, [10_000, 10_000, 3_000])
  assert.equal(clock, 30_000)
})

// pending 用伺服器給的時間，不把正常後端工作變成固定兩秒輪詢。
test('pending uses the server deadline before a terminal result', async () => {
  let calls = 0
  let clock = 0
  const waits: number[] = []
  const result = await recoverSubmission({ signal: new AbortController().signal,
    now: () => clock, wait: async (ms) => { waits.push(ms); clock += ms },
    resolve: async () => ++calls === 1 ? { status: 'pending', log_id: null, retry_after_ms: 4500 }
      : { status: 'failed', log_id: null, retry_after_ms: 0 },
  })
  assert.equal(result?.status, 'failed')
  assert.deepEqual(waits, [4500])
})

// 長於三十秒的伺服器截止時間只能交還一次性排程，不能拉長本輪或高頻輪詢。
test('a server deadline beyond the round budget returns pending without polling', async () => {
  let calls = 0
  const result = await recoverSubmission({ signal: new AbortController().signal,
    resolve: async () => { calls++; return { status: 'pending', log_id: null, retry_after_ms: 45_000 } },
    wait: async () => { assert.fail('must not exceed the round budget') },
  })
  assert.equal(calls, 1)
  assert.equal(result?.status, 'pending')
})

// 登入過期不重試，也不能清成確定失敗；由呼叫端導向重新登入。
test('401 is returned to session handling without retry', async () => {
  let calls = 0
  await assert.rejects(recoverSubmission({ signal: new AbortController().signal,
    resolve: async () => { calls++; throw new HttpStatusError(401, '') },
  }), HttpStatusError)
  assert.equal(calls, 1)
})

// 取消時連等待計時器都必須清除，後續不能發出舊帳號的恢復請求。
test('aborted recovery never dispatches and cancels pending waits', async () => {
  const controller = new AbortController()
  const waiting = waitForRecovery(30_000, controller.signal)
  controller.abort(new Error('account changed'))
  await assert.rejects(waiting, /account changed/)
  assert.equal(await recoverSubmission({ signal: controller.signal,
    resolve: async () => { assert.fail('cancelled recovery must not send') },
  }), null)
})
