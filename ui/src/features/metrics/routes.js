export default [
    {
        path: '/metrics',
        name: 'metrics',
        component: () => import('@/features/metrics/MetricsExplorer.vue'),
    },
]
