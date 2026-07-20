import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import FundView from '../../modules/fund-dashboard/FundView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/fund/:code', name: 'fund', component: FundView, props: true },
  ],
})

export default router
