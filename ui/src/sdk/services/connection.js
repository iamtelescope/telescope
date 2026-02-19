import HTTP from '@/utils/http'

const http = new HTTP()

class ConnectionService {
    getConnection = async (pk) => {
        return await http.Get(`ui/v1/connections/${pk}`)
    }
    getConnections = async () => {
        return await http.Get('ui/v1/connections')
    }
    getUsableConnections = async () => {
        return await http.Get('ui/v1/connections/usable')
    }
    getConnectionNames = async () => {
        return await http.Get('ui/v1/connections/names')
    }
    create = async (data) => {
        return await http.Post('ui/v1/connections', data)
    }
    update = async (pk, data) => {
        return await http.Patch(`ui/v1/connections/${pk}`, data)
    }
    testConnection = async (kind, connectionData) => {
        return await http.Post(`ui/v1/services/testConnection/${kind}`, connectionData)
    }
    deleteConnection = async (pk) => {
        return await http.Delete(`ui/v1/connections/${pk}`)
    }
    getConnectionRoleBindings = async (pk) => {
        return await http.Get(`ui/v1/connections/${pk}/roleBindings`)
    }
    grantConnectionRole = async (pk, user, group, role) => {
        let data = {
            subject: {
                kind: null,
                name: null,
            },
            role: role.name,
        }
        if (user != null) {
            data['subject'] = { kind: 'user', name: user.username }
        }
        if (group != null) {
            data['subject'] = { kind: 'group', name: group.name }
        }
        return await http.Post(`ui/v1/connections/${pk}/grantRole`, data)
    }
    revokeConnectionRole = async (pk, user, group, role) => {
        let data = {
            subject: {
                kind: null,
                pk: null,
            },
            role: role,
        }
        if (user != null) {
            data['subject'] = { kind: 'user', name: user.username }
        }
        if (group != null) {
            data['subject'] = { kind: 'group', name: group.name }
        }
        return await http.Post(`ui/v1/connections/${pk}/revokeRole`, data)
    }
}

export { ConnectionService }
