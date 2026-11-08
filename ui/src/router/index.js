import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { storeToRefs } from 'pinia'

import ExploreView from '../views/sources/ExploreView.vue'
import HomeView from '../views/RootView.vue'
import { featureRoutes } from '@/features/registry.js'
import { setPageTitle } from '@/components/common/pageTitle'

// Browser tab titles by route name; feature routes are listed here too.
const TITLES = {
    root: 'Logs',
    logs: 'Logs',
    explore: (r) => `${r.params.sourceSlug} · Explore`,
    userProfile: 'Profile',
    apiTokenNew: 'New API token',
    dashboards: 'Dashboards',
    dashboard: 'Dashboard',
    dashboardTemplates: 'Dashboard templates',
    sources: 'Sources',
    source: (r) => `${r.params.sourceSlug} · Source`,
    sourceNew: 'New source',
    sourceEdit: (r) => `Edit ${r.params.sourceSlug}`,
    connections: 'Connections',
    connection: 'Connection',
    connectionNew: 'New connection',
    connectionEdit: 'Edit connection',
    rbac: 'Access control',
    rbacUsers: 'Users',
    rbacGroups: 'Groups',
    rbacGroup: 'Group',
    rbacGroupNew: 'New group',
    rbacGroupEdit: 'Edit group',
    rbacRoles: 'Roles',
    alerts: 'Alerts',
    alertNew: 'New alert',
    alert: 'Edit alert',
    alertDetail: 'Alert history',
    alertChannels: 'Alert channels',
    charts: 'Chart explorer',
    metrics: 'Metrics',
    serviceMap: 'Service map',
    trace: (r) => `Trace ${String(r.params.traceId).slice(0, 8)}…`,
    notFound: 'Page not found',
}

const routes = [
    {
        path: '/',
        name: 'root',
        meta: {
            label: 'Logs',
        },
        component: HomeView,
    },
    {
        path: '/logs',
        name: 'logs',
        component: () => import('@/components/logs/Logs.vue'),
    },
    {
        path: '/profile',
        name: 'userProfile',
        component: () => import('@/components/user/UserProfile.vue'),
    },
    {
        path: '/profile/new_api_token',
        name: 'apiTokenNew',
        component: () => import('@/components/user/ApiTokenNew.vue'),
    },
    {
        path: '/dashboards',
        name: 'dashboards',
        component: () => import('@/views/dashboards/DashboardsView.vue'),
    },
    {
        path: '/dashboards/:dashboardSlug',
        name: 'dashboard',
        component: () => import('@/views/dashboards/DashboardView.vue'),
    },
    {
        path: '/sources',
        name: 'sources',
        component: () => import('@/components/sources/Sources.vue'),
    },
    {
        path: '/connections',
        name: 'connections',
        component: () => import('@/components/connections/Connections.vue'),
    },
    {
        path: '/connections/new',
        name: 'connectionNew',
        component: () => import('@/components/connections/ConnectionNew.vue'),
    },
    {
        path: '/connections/:connectionId',
        name: 'connection',
        component: () => import('@/components/connections/Connection.vue'),
    },
    {
        path: '/connections/:connectionId/edit',
        name: 'connectionEdit',
        component: () => import('@/components/connections/ConnectionEdit.vue'),
    },
    {
        path: '/sources/:sourceSlug/explore',
        name: 'explore',
        component: ExploreView,
    },
    {
        path: '/sources/new',
        name: 'sourceNew',
        component: () => import('@/components/sources/SourceNew.vue'),
    },
    {
        path: '/sources/:sourceSlug',
        name: 'source',
        component: () => import('@/components/sources/Source.vue'),
    },
    {
        path: '/sources/:sourceSlug/edit',
        name: 'sourceEdit',
        component: () => import('@/components/sources/SourceEdit.vue'),
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
        path: '/rbac/roles',
        name: 'rbacRoles',
        component: () => import('@/components/rbac/Roles.vue'),
    },
    ...featureRoutes,
    {
        path: '/:pathMatch(.*)*',
        name: 'notFound',
        component: () => import('@/components/common/NotFound.vue'),
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

router.beforeEach(async (to, from) => {
    const { isLoggedIn } = storeToRefs(useAuthStore())

    if (!isLoggedIn.value && to.name !== 'login') {
        window.location = 'login'
    }
})

router.afterEach((to) => {
    const t = TITLES[to.name]
    setPageTitle(typeof t === 'function' ? t(to) : t)
})

export default router
