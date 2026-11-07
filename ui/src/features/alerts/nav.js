import { Bell } from 'lucide-vue-next'

export default [
    {
        section: 'explore',
        label: 'Alerts',
        to: '/alerts',
        icon: Bell,
        routeNames: ['alerts', 'alertNew', 'alert', 'alertDetail', 'alertChannels'],
        testid: 'nav-alerts',
    },
]
