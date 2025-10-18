import HTTP from '@/utils/http'

const http = new HTTP()

class RoleService {
    getRole = async (roleType, roleName) => {
        let response = await http.Get(`ui/v1/rbac/roles/${roleType}/${roleName}`)
        return response
    }
    getRoles = async () => {
        let response = await http.Get('ui/v1/rbac/roles')
        return response
    }
}

export { RoleService }
