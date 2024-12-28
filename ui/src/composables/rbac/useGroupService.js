import { ref } from 'vue'
import { Group } from '@/sdk/models/rbac'
import { GroupService } from '@/sdk/services/Group'

const srv = new GroupService()

const useGetGroups = () => {
    const groups = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getGroups()
        if (response.result) {
            groups.value = response.data.map((item) => new Group(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { groups, error, loading, load }
}

const useGetSimpleGroups = () => {
    const groups = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getSimpleGroups()
        if (response.result) {
            groups.value = response.data.map((item) => new Group(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { groups, error, loading, load }
}


const useGetGroup = (groupId) => {
    const group = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getGroup(groupId)
        if (response.result) {
            group.value = new Group(response.data)
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { group, error, loading, load }
}

export { useGetGroup, useGetGroups, useGetSimpleGroups }
