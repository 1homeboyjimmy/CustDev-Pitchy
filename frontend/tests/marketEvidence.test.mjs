import test from 'node:test'
import assert from 'node:assert/strict'
import { sourceLink, unreadReason, searchProblems } from '../src/utils/marketEvidence.js'

test('source and reply links reject executable URLs and embedded credentials', () => {
  assert.equal(sourceLink('javascript:alert(1)'), null)
  assert.equal(sourceLink('https://user:password@example.com'), null)
  assert.equal(sourceLink('/relative'), null)
  assert.equal(sourceLink('https://reddit.com/r/a/comments/123/#reply'), 'https://reddit.com/r/a/comments/123/#reply')
})

test('failed searches remain distinct from searches with no matching results', () => {
  const states = [{ id: 'x', search_status: 'unavailable' }, { id: 'reddit', search_status: 'empty' },
    { id: 'habr_vc', search_status: 'timed_out' }]
  assert.deepEqual(searchProblems(states).map(item => item.id), ['x', 'habr_vc'])
  assert.equal(unreadReason('not_attempted'), 'Достигнут лимит страниц')
  assert.equal(unreadReason('timed_out'), 'Не хватило времени')
})
