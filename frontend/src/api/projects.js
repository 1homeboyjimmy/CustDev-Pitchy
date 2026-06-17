import service from './index'

/** Список проектов текущего пользователя с главного Pitchy. */
export const listProjects = () => service.get('/api/projects/list')

/** Паспорт выбранного проекта. */
export const getProjectPassport = (projectId) => service.get(`/api/projects/${projectId}/passport`)
