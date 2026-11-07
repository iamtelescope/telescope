export default [
    {
        path: '/alerts',
        name: 'alerts',
        component: () => import('@/features/alerts/AlertsView.vue'),
    },
    {
        path: '/alerts/new',
        name: 'alertNew',
        component: () => import('@/features/alerts/AlertEditor.vue'),
    },
    {
        path: '/alerts/channels',
        name: 'alertChannels',
        component: () => import('@/features/alerts/ChannelsView.vue'),
    },
    {
        path: '/alerts/:alertId(\\d+)',
        name: 'alert',
        component: () => import('@/features/alerts/AlertEditor.vue'),
    },
]
