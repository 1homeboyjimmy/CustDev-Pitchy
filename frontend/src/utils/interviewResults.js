// The API wraps IPC replies in data.result.results. Ignore response metadata.
export const normaliseInterviewResults = (payload) => {
  const results = payload?.data?.result?.results ?? payload?.data?.results
    ?? payload?.result?.results ?? payload?.results ?? payload
  if (!results || typeof results !== 'object' || Array.isArray(results)) return {}
  return Object.fromEntries(Object.entries(results).filter(([key, value]) => {
    const text = typeof value === 'string' ? value : (value?.response || value?.answer)
    return /^(reddit|twitter)_\d+$/.test(key) && typeof text === 'string' && text.trim() && value?.success !== false
  }))
}
