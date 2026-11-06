/** Keep the user's question authoritative, even when project context is long. */
export function researchRequirement(question, segments) {
  return `Провести синтетические кастдев-интервью по исходному продуктовому вопросу: ${question}. ` +
    `Затронутые группы: ${segments || 'не указаны'}. ` +
    'Исследовать различные позиции, возражения и условия решения без заранее заданного ответа.'
}

export function researchQuery({ question, name, problem, solution }) {
  return [question && `Исходный вопрос: ${question}`, name && `Проект: ${name}`,
    problem && `Текущая ситуация: ${problem}`, solution && `Предлагаемое изменение: ${solution}`]
    .filter(Boolean).join('. ').slice(0, 1800)
}
