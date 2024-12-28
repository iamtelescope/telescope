import { ref } from 'vue'
import { Role } from '@/sdk/models/rbac'
import { RoleService } from '@/sdk/services/Role'

const srv = new RoleService()

const useGetRole = (roleType, roleName) => {
    const role = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getRole(roleType, roleName)
        if (response.result) {
            role.value = new Role(response.data)
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { role, error, loading, load }
}

const useGetRoles = () => {
    const roles = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getRoles()
        if (response.result) {
            roles.value = response.data.map((item) => new Role(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { roles, error, loading, load }
}

export { useGetRole, useGetRoles }
