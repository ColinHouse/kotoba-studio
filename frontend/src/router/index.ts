import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/sources', name: 'sources', component: () => import('@/views/SourcesView.vue') },
    { path: '/capture', name: 'capture', component: () => import('@/views/CaptureView.vue') },
    { path: '/inbox', name: 'inbox', component: () => import('@/views/InboxView.vue') },
    { path: '/review', name: 'review', component: () => import('@/views/ReviewView.vue') },
    { path: '/stats', name: 'stats', component: () => import('@/views/StatsView.vue') },
    {
      path: '/quiz/:sessionId',
      name: 'quiz',
      component: () => import('@/views/QuizView.vue'),
      props: true,
    },
    { path: '/library', name: 'library', component: () => import('@/views/LibraryView.vue') },
    { path: '/kanji', name: 'kanji', component: () => import('@/views/KanjiView.vue') },
    {
      path: '/read/:sourceId',
      name: 'reader',
      component: () => import('@/views/ReaderView.vue'),
      props: true,
    },
    {
      path: '/terms/:id',
      name: 'term',
      component: () => import('@/views/TermDetailView.vue'),
      props: true,
    },
    { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
  ],
})
