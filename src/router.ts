import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'dashboard', component: () => import('./views/DashboardView.vue') },
  { path: '/browse', name: 'browse', component: () => import('./views/BrowseView.vue') },
  { path: '/messages', name: 'messages', component: () => import('./views/MessagesView.vue') },
  { path: '/messages/:id', name: 'message-detail', component: () => import('./views/MessageDetailView.vue') },
  { path: '/search', name: 'search', component: () => import('./views/SearchView.vue') },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
