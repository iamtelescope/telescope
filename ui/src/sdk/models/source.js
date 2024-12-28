import { getDefaultIfUndefined } from '@/utils/utils'
import { User, Group } from '@/sdk/models/rbac'

const SourceKinds = [
    'clickhouse'
]

class Source {
    constructor(data) {
        this.kind = data.kind
        this.slug = data.slug
        this.name = data.name
        this.description = data.description
        this.timeField = data.time_field
        this.uniqField = data.uniq_field
        this.severityField = data.severity_field
        this.fields = data.fields
        this.defaultChosenFields = data.default_chosen_fields
        this.connection = getDefaultIfUndefined(data.connection, {})
        this.permissions = getDefaultIfUndefined(data.permissions, [])
    }
    isEditable() {
        if (this.permissions.includes('edit')) {
            return true
        } else {
            return false
        }
    }
    isGrantable() {
        if (this.permissions.includes('grant')) {
            return true
        } else {
            return false
        }
    }
}

class SourceRoleBiding {
    constructor(data) {
        this.user = data.user ? new User(data.user) : null
        this.group = data.group ? new Group(data.group) : null
        this.role = data.role
    }
}

export { Source, SourceKinds, SourceRoleBiding}