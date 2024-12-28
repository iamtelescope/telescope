import HTTP from '@/utils/http'

const http = new HTTP()

class GroupService {
    createGroup = async (groupName) => {
        let data = {'name': groupName}
        let response = await http.Post('/ui/v1/rbac/groups', data)
        return response
    }
    deleteGroup = async (groupId) => {
        let response = await http.Delete(`/ui/v1/rbac/groups/${groupId}`)
        return response
    }
    updateGroup = async (groupId, groupName) => {
        let data = {'name': groupName}
        let response = await http.Patch(`/ui/v1/rbac/groups/${groupId}`, data)
        return response
    }
    getGroup = async (groupId) => {
        let response = await http.Get(`/ui/v1/rbac/groups/${groupId}`)
        return response
    }
    getGroups = async () => {
        let response = await http.Get('/ui/v1/rbac/groups')
        return response
    }
    getSimpleGroups = async () => {
        let response = await http.Get('/ui/v1/rbac/simplegroups')
        return response
    }
    addUsers = async (groupId, usersIds) => {
        let data = { 'ids': usersIds }
        let response = await http.Post(`/ui/v1/rbac/groups/${groupId}/addUsers`, data)
        return response
    }
    removeUsers = async (groupId, usersIds) => {
        let data = { 'ids': usersIds }
        let response = await http.Post(`/ui/v1/rbac/groups/${groupId}/removeUsers`, data)
        return response
    }
    grantRole = async (groupId, roleName) => {
        let data = {'role': roleName}
        let response = await http.Post(`/ui/v1/rbac/groups/${groupId}/grantRole`, data)
        return response
    }
    revokeRole = async (groupId, roleName) => {
        let data = {'role': roleName}
        let response = await http.Post(`/ui/v1/rbac/groups/${groupId}/revokeRole`, data)
        return response
    }
}

export { GroupService }