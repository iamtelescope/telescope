import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { storeToRefs } from 'pinia'

import LogsView from '../views/sources/LogsView.vue'
import HomeView from '../views/RootView.vue'

const routes = [
  {
    path: '/',
    name: 'root',
    meta: {
      label: "Sources",
    },
    component: HomeView,
  },
  {
    path: '/sources',
    name: 'sources',
    component: () => import('@/components/sources/Sources.vue')
  },
  {
    path: '/sources/:sourceSlug/logs',
    name: 'logs',
    component: LogsView,
  },
  {
    path: '/sources/new',
    name: 'sourceNew',
    component: () => import('@/components/sources/SourceNew.vue')
  },
  {
    path: '/sources/:sourceSlug',
    name: 'source',
    component: () => import('@/components/sources/Source.vue')
  },
  {
    path: '/sources/:sourceSlug/edit',
    name: 'sourceEdit',
    component: () => import('@/components/sources/SourceEdit.vue')
  },
  {
    path: '/rbac/groups/new',
    name: 'rbacGroupNew',
    component: () => import('@/components/rbac/GroupNew.vue'),
  },
  {
    path: '/rbac',
    name: 'rbac',
    component: () => import('@/components/rbac/rbac.vue'),
  },
  {
    path: '/rbac/groups/:groupId',
    name: 'rbacGroup',
    component: () => import('@/components/rbac/Group.vue'),
  },
  {
    path: '/rbac/groups/:groupId/edit',
    name: 'rbacGroupEdit',
    component: () => import('@/components/rbac/GroupEdit.vue'),
  },
  {
    path: '/rbac/groups',
    name: 'rbacGroups',
    component: () => import('@/components/rbac/Groups.vue'),
  },
  {
    path: '/rbac/users',
    name: 'rbacUsers',
    component: () => import('@/components/rbac/Users.vue'),
  },
  {
    path: '/rbac/roles/:roleType/:roleName',
    name: 'rbacRole',
    component: () => import('@/components/rbac/Role.vue'),
  },
  {
    path: '/rbac/roles',
    name: 'rbacRoles',
    component: () => import('@/components/rbac/Roles.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

router.beforeEach(async (to, from) => {
  const { isLoggedIn } = storeToRefs(useAuthStore())

  if (
    !isLoggedIn.value &&
    to.name !== 'login'
  ) {
    window.location = '/login'
  }
})

export default router
