import HTTP from '@/utils/http'

const http = new HTTP()

class AuthService {
    getCurrentUser = async () => {
        let response = await http.Get('/ui/v1/auth/whoami')
        return response
    }
}

export { AuthService }