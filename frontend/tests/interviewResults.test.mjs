import test from 'node:test'
import assert from 'node:assert/strict'
import { normaliseInterviewResults } from '../src/utils/interviewResults.js'

test('unwraps the actual API and IPC response without losing agent answers', () => {
  const results = { reddit_2: { response: 'Ответ респондента' } }
  assert.deepEqual(normaliseInterviewResults({ success: true, data: {
    success: true, interviews_count: 1, result: { interviews_count: 1, results }, timestamp: 'now',
  } }), results)
})

test('accepts a direct result map and ignores metadata or empty answers', () => {
  assert.deepEqual(normaliseInterviewResults({ reddit_0: { response: 'Готов обсудить' }, reddit_1: { response: '' },
    success: true, timestamp: 'now', interviews_count: 2 }), { reddit_0: { response: 'Готов обсудить' } })
})

test('failed or missing interview responses are not saved as completed interviews', () => {
  assert.deepEqual(normaliseInterviewResults({ reddit_0: { response: 'error', success: false } }), {})
  assert.deepEqual(normaliseInterviewResults(null), {})
})
