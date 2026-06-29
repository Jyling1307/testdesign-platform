import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'ProjectList',
      component: () => import('../views/ProjectList.vue'),
    },
    {
      path: '/project/:id',
      name: 'ProjectDetail',
      component: () => import('../views/ProjectDetail.vue'),
      children: [
        { path: 'documents', name: 'DocumentUpload', component: () => import('../views/DocumentUpload.vue') },
        { path: 'designs', name: 'TestDesignView', component: () => import('../views/TestDesignView.vue') },
        { path: 'knowledge', name: 'KnowledgeSearch', component: () => import('../views/KnowledgeSearch.vue') },
      ],
    },
  ],
})

export default router
