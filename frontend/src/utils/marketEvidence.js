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
    invalid_url: 'Некорректная ссылка' })[status] || 'Не удалось прочитать'
}

export function searchProblems(states) {
  return (Array.isArray(states) ? states : []).filter(item =>
    item && ['unavailable', 'timed_out'].includes(item.search_status || item.status))
}
