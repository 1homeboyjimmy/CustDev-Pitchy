import service, { requestWithRetry } from './index'

/**
 * Start report generation
 * @param {Object} data - { simulation_id, force_regenerate? }
 */
export const generateReport = (data) => {
  // Background generation is non-idempotent; retrying a lost response can
  // start multiple report workers for the same simulation.
  return service.post('/api/report/generate', data)
}

/**
 * Get report generation status
 * @param {string} reportId
 */
export const getReportStatus = ({ taskId, simulationId } = {}) => {
  return service.get('/api/report/generate/status', {
    params: {
      ...(taskId ? { task_id: taskId } : {}),
      ...(simulationId ? { simulation_id: simulationId } : {}),
    }
  })
}

/**
 * Get Agent log (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start from which line
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })
}

/**
 * Get console log (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start from which line
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })
}

/**
 * Get report details
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`)
}

/**
 * Chat with Report Agent
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/chat', data), 3, 1000)
}
