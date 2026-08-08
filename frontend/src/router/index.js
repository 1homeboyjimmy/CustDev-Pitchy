import { createRouter, createWebHistory } from 'vue-router'
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: () => import('../views/MainView.vue'),
    props: true
  },
  {
    path: '/signals',
    name: 'Signals',
    component: () => import('../views/SignalsView.vue')
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: () => import('../views/SimulationView.vue'),
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: () => import('../views/SimulationRunView.vue'),
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: () => import('../views/ReportView.vue'),
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: () => import('../views/InteractionView.vue'),
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Гейт: без валидной сессии главного сайта в CustDev не пускаем.
import { getMe } from '../api/auth'
let authState = null // null=неизвестно, true/false

router.beforeEach(async (to, from, next) => {
  if (authState === true) return next()
  if (authState === false) { window.location.href = MAIN_LOGIN_URL; return }
  try {
    const res = await getMe()
    authState = !!(res && res.success)
  } catch (e) {
    // 401 → запускаем бесшовный SSO через основной Pitchy. Сетевая ошибка
    // → не лочим, API сам покажет ошибку.
    authState = e?.response?.status === 401 ? false : true
  }
  if (authState) return next()
  window.location.href = `/api/auth/start?next=${encodeURIComponent(to.fullPath)}`
})

export default router
