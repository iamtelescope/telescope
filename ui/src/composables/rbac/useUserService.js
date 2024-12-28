import { ref } from 'vue'
import { User } from '@/sdk/models/rbac'
import { UserService } from '@/sdk/services/User'

const srv = new UserService()

const useGetUsers = () => {
    const users = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getUsers()
        if (response.result) {
            users.value = response.data.map((item) => new User(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { users, error, loading, load }
}

const useGetSimpleUsers = () => {
    const users = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getSimpleUsers()
        if (response.result) {
            users.value = response.data.map((item) => new User(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { users, error, loading, load }
}

export { useGetUsers, useGetSimpleUsers }
