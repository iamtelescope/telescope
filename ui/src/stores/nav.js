import { defineStore } from 'pinia'

const navs = {
    rbac: { label: 'Role-Based Access Control', icon: 'pi pi-shield', url: '/rbac' },
    groups: { label: 'Groups', icon: 'pi pi-users', url: '/rbac/groups' },
    users: { label: 'Users', icon: 'pi pi-user', url: '/rbac/users' },
    profile: { label: 'Profile', icon: 'pi pi-user', url: '/profile' },
    sources: { label: 'Sources', icon: 'pi pi-database', url: '/sources' },
}

export const useNavStore = defineStore('nav', {
    state: () => ({ items: [] }),

    actions: {
        update(items) {
            this.items = items
        },
        append(item) {
            this.items.push(item)
        },
        updatev2(items) {
            let result = []
            for (let i in items) {
                let key = items[i]
                if (key in navs) {
                    result.push(navs[key])
                } else {
                    if (typeof key === 'string' || key instanceof String) {
                        result.push({ label: key })
                    } else {
                        result.push(key)
                    }
                }
            }
            this.items = result
        },
    },
})
