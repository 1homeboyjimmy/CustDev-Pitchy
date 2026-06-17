import service, { requestWithRetry } from './index'

/**
 * Сгенерировать финальный отчёт «Сигналы × Симуляция».
 * @param {Object} data - { simulation_id, query }
 * @returns data: { signals, custdev_count, verdict, report_markdown, available }
 */
export const generateVerdict = (data) => {
  return requestWithRetry(() => service.post('/api/verdict/generate', data), 2, 1500)
}
