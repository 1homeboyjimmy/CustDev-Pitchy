import service from './index'

/**
 * Get current user information (check session)
 */
export function getMe() {
  return service({
    url: '/api/auth/me',
    method: 'get'
  })
}
