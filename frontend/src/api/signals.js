import service, { requestWithRetry } from './index'

/**
 * Сканировать реальные сигналы рынка (боли/спрос) по гипотезе.
 * @param {Object} data - { query, max_results? }
 * @returns {Promise} data: { available, sources:[{title,url,domain,highlights}], context, query }
 */
export const scanSignals = (data) => {
  return requestWithRetry(() => service.post('/api/signals/scan', data), 2, 1000)
}
