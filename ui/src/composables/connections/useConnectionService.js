import { ref } from 'vue'
import { Connection, ConnectionRoleBinding } from '@/sdk/models/connection'
import { ConnectionService } from '@/sdk/services/connection'

const srv = new ConnectionService()

const useGetConnections = () => {
    const connections = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getConnections()
        if (response.result) {
            connections.value = response.data.map((item) => new Connection(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { connections, error, loading, load }
}

const useGetConnection = (pk) => {
    const connection = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getConnection(pk)
        if (response.result) {
            connection.value = new Connection(response.data)
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { connection, error, loading, load }
}

const useGetConnectionRoleBindings = (pk) => {
    const bindings = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getConnectionRoleBindings(pk)
        if (response.result) {
            bindings.value = response.data.map((item) => new ConnectionRoleBinding(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { bindings, error, loading, load }
}

const useGetUsableConnections = () => {
    const connections = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getUsableConnections()
        if (response.result) {
            connections.value = response.data.map((item) => new Connection(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { connections, error, loading, load }
}

const useGetConnectionNames = () => {
    const connectionNames = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getConnectionNames()
        if (response.result) {
            connectionNames.value = response.data
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { connectionNames, error, loading, load }
}

export {
    useGetConnection,
    useGetConnections,
    useGetConnectionRoleBindings,
    useGetUsableConnections,
    useGetConnectionNames,
}
