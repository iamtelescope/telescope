import HTTP from '@/utils/http'

const http = new HTTP()

class UserService {
    getUsers = async () => {
        let response = await http.Get('/ui/v1/rbac/users')
        return response
    }
    getSimpleUsers = async () => {
        let response = await http.Get('/ui/v1/rbac/simpleusers')
        return response
    }
}
export { UserService }