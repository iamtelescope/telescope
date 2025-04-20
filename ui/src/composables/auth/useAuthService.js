import { ref } from 'vue'
import { User } from '@/sdk/models/rbac'
import { APIToken } from '@/sdk/models/auth'
import { AuthService } from '@/sdk/services/Auth'
import { Source } from '@/sdk/models/source'

const srv = new AuthService()

const useGetCurrentUser = () => {
    const user = ref(null)
    const error = ref(null)

    const load = async () => {
        let response = await srv.getCurrentUser()
        if (response.result) {
            user.value = new User(response.data)
        } else {
            error.value = response.errors.join(', ')
        }
    }
    return { user, error, load }
}

const useGetCurrentUserAPITokens = () => {
    const tokens = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getCurrentUserAPITokens()
        if (response.result) {
            tokens.value = response.data.map((item) => new APIToken(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { tokens, error, loading, load }
}

export { useGetCurrentUser, useGetCurrentUserAPITokens }
