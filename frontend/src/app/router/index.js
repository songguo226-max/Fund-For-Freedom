import { createRouter, createWebHistory } from 'vue-router'
import HomeDashboardView from '../views/HomeDashboardView.vue'
import DataView from '../views/DataView.vue'
import InformationView from '../views/InformationView.vue'
import MethodologyView from '../views/MethodologyView.vue'
import FundView from '../../modules/fund-dashboard/FundView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeDashboardView },
    { path: '/information', name: 'information', component: InformationView },
    { path: '/data', name: 'data', component: DataView },
    { path: '/methodology', name: 'methodology', component: MethodologyView },
    { path: '/fund/:code', name: 'fund', component: FundView, props: true },
  ],
})

export default router
