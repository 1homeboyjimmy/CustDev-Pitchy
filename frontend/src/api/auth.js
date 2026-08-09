import service from './index'

let mePromise = null
let meCache = null
let meCacheUntil = 0

/**
 * Get current user information (check session)
 */
export function getMe() {
  const now = Date.now()
  if (meCache && now < meCacheUntil) return Promise.resolve(meCache)
  if (mePromise) return mePromise

  mePromise = service({
    url: '/api/auth/me',
    method: 'get'
  })
    .then((response) => {
      meCache = response
      meCacheUntil = Date.now() + 30_000
      return response
    })
    .finally(() => {
      mePromise = null
    })

  return mePromise
}
