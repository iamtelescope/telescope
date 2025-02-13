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
        // this.uniqField = data.uniq_field
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
    generateFieldsExample() {
        let fields = []
        for (const field in this.fields) {
            fields.push(field)
        }
        return fields.join(', ')
    }
    generateFlyQLExample() {
        let text = ''
        let fields = []
        for (const [field, data] of Object.entries(this.fields)) {
            if (data.type == 'string' && fields.length < 4) {
                fields.push(field)
            }
        }
        if (fields.length == 1) {
            text += `${fields[0]}=*value*`
        } else if (fields.length == 2 || fields.length == 3) {
            text += `${fields[0]}=*value* and ${fields[1]!="value"}`
        }
        if (fields.length == 4) {
            text += `${fields[0]}="*like value*" and ${fields[1]}!=value or (${fields[2]}=~".*rege[xX]$" and ${fields[3]}!~"reg ex$")`
        }
        return text
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
