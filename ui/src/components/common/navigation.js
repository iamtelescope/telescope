import { Cable, Database, KeyRound, LayoutDashboard, ScrollText, UserPlus, Users } from 'lucide-vue-next'
import { featureNav } from '@/features/registry.js'

// The app's navigation, shared by the sidebar and the command palette.
const CORE = [
    {
        section: 'explore',
        label: 'Logs',
        to: '/',
        icon: ScrollText,
        routeNames: ['root', 'explore', 'logs'],
        keywords: 'search explore sources events',
    },
    {
        section: 'explore',
        label: 'Dashboards',
        to: '/dashboards',
        icon: LayoutDashboard,
        routeNames: ['dashboards', 'dashboard', 'dashboardTemplates'],
        testid: 'nav-dashboards',
        keywords: 'charts boards',
    },
    {
        section: 'data',
        label: 'Connections',
        to: '/connections',
        icon: Cable,
        routeNames: ['connections', 'connection', 'connectionNew', 'connectionEdit'],
        keywords: 'clickhouse database server',
    },
    {
        section: 'data',
        label: 'Sources',
        to: '/sources',
        icon: Database,
        routeNames: ['sources', 'source', 'sourceEdit', 'sourceNew'],
        keywords: 'tables data',
    },
    {
        section: 'admin',
        label: 'Users',
        to: '/rbac/users',
        icon: Users,
        routeNames: ['rbacUsers'],
        keywords: 'rbac people',
    },
    {
        section: 'admin',
        label: 'Groups',
        to: '/rbac/groups',
        icon: UserPlus,
        routeNames: ['rbacGroups', 'rbacGroup', 'rbacGroupNew', 'rbacGroupEdit'],
        keywords: 'rbac teams',
    },
    {
        section: 'admin',
        label: 'Roles',
        to: '/rbac/roles',
        icon: KeyRound,
        routeNames: ['rbacRoles'],
        testid: 'nav-roles',
        keywords: 'rbac permissions',
    },
]

const SECTIONS = [
    { id: 'explore', label: 'Explore' },
    { id: 'data', label: 'Data' },
    { id: 'admin', label: 'Administration', adminOnly: true },
]

const items = (section) => [
    ...CORE.filter((i) => i.section === section),
    ...featureNav.filter((i) => (i.section || 'explore') === section),
]

// Core entries come first in each section, then the feature entries.
export const navSections = (user) =>
    SECTIONS.filter((s) => !s.adminOnly || user?.hasAccessToSettings?.()).map((s) => ({ ...s, items: items(s.id) }))

export const isNavItemActive = (item, route) => (item.routeNames || []).includes(route.name)
