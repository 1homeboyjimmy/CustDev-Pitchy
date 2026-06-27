import service, { requestWithRetry } from './index'

/**
 * Сканировать реальные сигналы рынка (боли/спрос) по гипотезе.
 * @param {Object} data - { query, max_results? }
 * @returns {Promise} data: { available, sources:[{title,url,domain,highlights}], context, query }
 */
export const scanSignals = (data) => {
  return requestWithRetry(() => service.post('/api/signals/scan', data), 2, 1000)
}

/**
 * Запустить рой research-агентов (фон). data: { query, segments? } → { task_id }
 */
export const startSignalsResearch = (data) => {
  return requestWithRetry(() => service.post('/api/signals/research', data), 2, 1000)
}

/**
 * Статус разведки (опрос): прогресс агентов + итоговый результат.
 */
export const getSignalsResearchStatus = (taskId) => {
  return service.get('/api/signals/research/status', { params: { task_id: taskId } })
}

/**
 * Прикрепить результат разведки к прогону (фон, после создания симуляции).
 * data: { simulation_id, result }
 */
export const attachSignals = (data) => {
  return service.post('/api/signals/attach', data)
}

/**
 * Получить сохранённые сигналы прогона по simulation_id (read-only из истории).
 */
export const getSavedSignals = (simulationId) => {
  return service.get('/api/signals/saved', { params: { simulation_id: simulationId } })
}
