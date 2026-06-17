import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import SignalsView from '../views/SignalsView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/signals',
    name: 'Signals',
    component: SignalsView
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Гейт: без валидной сессии главного сайта в CustDev не пускаем.
import { getMe } from '../api/auth'
const MAIN_LOGIN_URL = 'https://pitchy.pro/login'
let authState = null // null=неизвестно, true/false

router.beforeEach(async (to, from, next) => {
  if (authState === true) return next()
  if (authState === false) { window.location.href = MAIN_LOGIN_URL; return }
  try {
    const res = await getMe()
    authState = !!(res && res.success)
  } catch (e) {
    // 401 → нет сессии (редирект). Сетевая ошибка → не лочим (API сам ответит 401).
    authState = e?.response?.status === 401 ? false : true
  }
  if (authState) return next()
  window.location.href = MAIN_LOGIN_URL
})

export default router
