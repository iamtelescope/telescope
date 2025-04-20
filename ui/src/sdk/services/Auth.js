import HTTP from '@/utils/http'

const http = new HTTP()

class AuthService {
    getCurrentUser = async () => {
        let response = await http.Get('/ui/v1/auth/whoami')
        return response
    }
    getCurrentUserAPITokens = async () => {
        let response = await http.Get('/ui/v1/auth/api_tokens')
        return response
    }
    createAPIToken = async (data) => {
        let response = await http.Post('/ui/v1/auth/api_tokens', data)
        return response
    }
    deleteCurrentUserAPITokens = async (tokens) => {
        let data = { tokens: tokens }
        let response = await http.Post('/ui/v1/auth/api_tokens/delete', data)
        return response
    }
}

export { AuthService }
