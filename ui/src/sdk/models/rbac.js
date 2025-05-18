import { getDefaultIfUndefined } from '@/utils/utils'

class User {
    constructor(data) {
        this.id = data.id
        this.isActive = data.is_active
        this.username = data.username
        this.firstName = getDefaultIfUndefined(data.first_name, '')
        this.lastName = getDefaultIfUndefined(data.last_name, '')
        this.lastLogin = getDefaultIfUndefined(data.last_login, '')
        this.type = getDefaultIfUndefined(data.type, 'local')
        this.avatarUrl = getDefaultIfUndefined(data.avatar_url, '')
        this.permissions = getDefaultIfUndefined(data.permissions, [])
        this.groups = getDefaultIfUndefined(data.groups, [])
    }

    get displayGroups() {
        let values = []
        for (var idx in this.groups) {
            values.push(this.groups[idx].name)
        }
        if (values.length > 0) {
            return values.join(', ')
        } else {
            return '-'
        }
    }

    get displayFirstName() {
        return this.firstName || '-'
    }

    get displayLastName() {
        return this.lastName || '-'
    }

    get displayLastLogin() {
        return this.lastLogin || '-'
    }

    get displayFull() {
        let value = this.username
        if (this.firstName && this.lastName) {
            value += ` (${this.firstName} ${this.lastName})`
        }
        return value
    }

    get sortedGroups() {
        return this.groups.sort((a, b) => a.name.localeCompare(b.name))
    }

    hasAccessToSettings() {
        if (this.permissions.includes('manage_rbac')) {
            return true
        } else {
            return false
        }
    }

    canCreateSource() {
        if (this.permissions.includes('global_create_source')) {
            return true
        } else {
            return false
        }
    }
}

class Group {
    constructor(data) {
        this.id = data.id
        this.name = data.name
        this.userCount = getDefaultIfUndefined(data.user_count, 0)
        this.users = getDefaultIfUndefined(data.users, [])
        if (this.users.length > 0) {
            this.users = this.users.map((item) => new User(item))
        }
        this.roles = getDefaultIfUndefined(data.roles, [])
    }
}

class Role {
    constructor(data) {
        this.name = data.name
        this.users = getDefaultIfUndefined(data.users, 0)
        this.groups = getDefaultIfUndefined(data.groups, 0)
        this.permissions = getDefaultIfUndefined(data.permissions, [])
        this.type = getDefaultIfUndefined(data.type, '')
    }
}

export { User, Group, Role }
