export default [
    {
        path: '/dashboards/templates',
        name: 'dashboardTemplates',
        component: () => import('@/features/templates/TemplatesView.vue'),
    },
]
