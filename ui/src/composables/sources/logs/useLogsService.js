import { ref } from 'vue'
import { LogsService } from '@/sdk/services/Logs'

const srv = new LogsService()

const useGetLogs = () => {
    const rows = ref(null)
    const metadata = ref(null)
    const error = ref(null)
    const loading = ref(null)
    const validation = ref(null)

    const load = async (slug, params) => {
        loading.value = true
        let response = await srv.getLogs(slug, params)
        if (response.result) {
            rows.value = response.data.rows
            metadata.value = response.data.metadata
        }
        error.value = response.errors.join(', ')
        validation.value = response.validation
        loading.value = false
    }
    return { rows, metadata, error, loading, validation, load}
}

export { useGetLogs }