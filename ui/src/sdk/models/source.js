import { getDefaultIfUndefined } from '@/utils/utils'
import { User, Group } from '@/sdk/models/rbac'

const SourceKinds = ['clickhouse', 'kubernetes']

class Source {
    constructor(data) {
        this.kind = data.kind
        this.slug = data.slug
        this.name = data.name
        this.description = data.description
        this.timeColumn = data.time_column
        this.dateColumn = data.date_column
        this.severityColumn = data.severity_column
        this.severityRules = data.severity_rules || null
        this.columns = data.columns
        this.contextColumns = data.context_columns
        this.defaultChosenColumns = data.default_chosen_columns
        this.supportRawQuery = data.support_raw_query
        this.executeQueryOnOpen = data.execute_query_on_open
        this.connection = getDefaultIfUndefined(data.connection, {})
        this.connectionId = data.connection_id
        this.conn = data.conn // Full connection object (when user has edit permissions)
        this.data = data.data || {} // Source-specific data (e.g., database, table for ClickHouse)
        this.permissions = getDefaultIfUndefined(data.permissions, [])
        this.queryMode = data.query_mode || 'separate'
        this.orderByExpression = data.order_by_expression || ''
    }
    isEditable() {
        if (this.permissions.includes('edit')) {
            return true
        } else {
            return false
        }
    }
    isReadable() {
        if (this.permissions.includes('read')) {
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
    isRawQueryAllowed() {
        if (this.permissions.includes('raw_query') && this.supportRawQuery) {
            return true
        } else {
            return false
        }
    }
    generateColumnsExample() {
        let columns = []
        for (const column in this.columns) {
            columns.push(column)
        }
        return columns.join(', ')
    }

    generateFlyQLExample() {
        let text = ''
        let columns = []
        for (const [column, data] of Object.entries(this.columns)) {
            if (data.type.toLowerCase().includes('string') && columns.length < 4) {
                columns.push(column)
            }
        }
        if (columns.length == 1) {
            text += `${columns[0]}=*value*`
        } else if (columns.length == 2 || columns.length == 3) {
            text += `${columns[0]}=*value* and ${columns[1] != 'value'}`
        }
        if (columns.length == 4) {
            text += `${columns[0]}="*like value*" and ${columns[1]}!=value or (${columns[2]}=~".*rege[xX]$" and ${columns[3]}!~"reg ex$")`
        }
        return text
    }

    generateRawQueryExample() {
        if (this.kind !== 'clickhouse') {
            return ''
        }
        let text = ''
        let columns = []
        for (const [column, data] of Object.entries(this.columns)) {
            if (data.type.toLowerCase().includes('string') && columns.length < 4) {
                columns.push(column)
            }
        }
        if (columns.length == 1) {
            text += `${columns[0]} = 'value'`
        } else if (columns.length == 2 || columns.length == 3) {
            text += `${columns[0]} = 'value' and ${columns[1] != 'value'}`
        }
        if (columns.length == 4) {
            text += `${columns[0]} LIKE "%value%" AND ${columns[1]} != 'value' OR match(${columns[2]}, '*rege[xX]$' AND NOT match(${columns[3]}, 'reg ex$')`
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

export { Source, SourceKinds, SourceRoleBiding }
