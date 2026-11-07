import { getDefaultIfUndefined } from '@/utils/utils'
import { User } from '@/sdk/models/rbac'

class Dashboard {
    constructor(data) {
        this.slug = data.slug
        this.name = data.name
        this.description = getDefaultIfUndefined(data.description, '')
        this.shared = data.shared
        this.data = data.data
        this.version = data.version
        this.owner = data.owner ? new User(data.owner) : null
        this.updatedBy = data.updated_by ? new User(data.updated_by) : null
        this.createdAt = data.created_at
        this.updatedAt = data.updated_at
        this.permissions = getDefaultIfUndefined(data.permissions, [])
        this.tilesCount = getDefaultIfUndefined(data.tiles_count, data.data?.tiles?.length ?? 0)
    }

    canEdit() {
        return this.permissions.includes('edit')
    }

    canDelete() {
        return this.permissions.includes('delete')
    }
}

export { Dashboard }
