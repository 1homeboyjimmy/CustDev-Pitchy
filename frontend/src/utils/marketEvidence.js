export function sourceLink(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}

export function unreadReason(status) {
  return ({ blocked: 'Доступ ограничен площадкой', timed_out: 'Не хватило времени',
    request_failed: 'Не удалось загрузить', unavailable: 'Сборщик недоступен',
    content_unavailable: 'Текст недоступен', unexpected_redirect: 'Перенаправление на другую площадку',
    not_attempted: 'Достигнут лимит страниц', browser_disabled: 'Требуется браузер',
    browser_unavailable: 'Браузер сборщика недоступен',
    http_error: 'Страница вернула ошибку', unsupported_content: 'Неподдерживаемый формат',
    document_text_unavailable: 'Не удалось извлечь текст документа',
    budget_limited: 'Достигнут лимит чтения API', api_unavailable: 'API площадки недоступен',
    invalid_url: 'Некорректная ссылка' })[status] || 'Не удалось прочитать'
}

export function searchProblems(states) {
  return (Array.isArray(states) ? states : []).filter(item =>
    item && ['unavailable', 'timed_out'].includes(item.search_status || item.status))
}

export function locatorLabel(value) {
  const locator = typeof value === 'string' ? value : ''
  if (/^pdf:page:\d+$/.test(locator)) return `PDF, страница ${locator.split(':')[2]}`
  if (/^comment:\d+$/.test(locator)) return `Комментарий ${Number(locator.split(':')[1]) + 1}`
  if (locator.startsWith('html:')) return locator.split(':').slice(2).join(':') || 'Фрагмент страницы'
  return 'Фрагмент страницы'
}
