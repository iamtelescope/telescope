export default [
    {
        path: '/sources/:sourceSlug/traces/:traceId',
        name: 'trace',
        component: () => import('@/features/traces/TraceView.vue'),
    },
]
