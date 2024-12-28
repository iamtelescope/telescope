import { ref } from 'vue'
import { User } from '@/sdk/models/rbac'
import { AuthService } from '@/sdk/services/Auth'

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

export { useGetCurrentUser }