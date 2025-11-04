import { getDefaultIfUndefined } from '@/utils/utils'
import { User, Group } from '@/sdk/models/rbac'

class Connection {
    constructor(data) {
        this.id = data.id
        this.kind = data.kind
        this.name = data.name
        this.data = data.data
        this.description = data.description
        this.createdAt = data.created_at
        this.updatedAt = data.updated_at
        this.permissions = getDefaultIfUndefined(data.permissions, [])
    }

    canEdit() {
        return this.permissions.includes('edit')
    }

    canDelete() {
        return this.permissions.includes('delete')
    }

    canGrant() {
        return this.permissions.includes('grant')
    }
}

class ConnectionRoleBinding {
    constructor(data) {
        this.user = data.user ? new User(data.user) : null
        this.group = data.group ? new Group(data.group) : null
        this.role = data.role
    }
}

export { Connection, ConnectionRoleBinding }
