import test from 'node:test'
import assert from 'node:assert/strict'
import { researchRequirement, researchQuery } from '../src/utils/productResearchInput.js'

test('the actual product question survives long project context without a forced demand goal', () => {
  const question = 'Как пользователи отреагируют на обязательную регистрацию?'
  const result = researchQuery({ question, name: 'Каталог', problem: 'Контекст '.repeat(1000), solution: 'Изменение' })
  assert.ok(result.startsWith(`Исходный вопрос: ${question}`))
  assert.ok(result.length <= 1800)
  const requirement = researchRequirement(question, 'Гости сайта')
  assert.ok(requirement.includes(question))
  assert.ok(requirement.includes('Гости сайта'))
  assert.ok(!requirement.includes('нужен ли рынку'))
  assert.ok(!requirement.includes('готовы платить'))
})
