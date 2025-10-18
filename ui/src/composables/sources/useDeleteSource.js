import { ref } from 'vue'
import HTTP from '@/utils/http'

const http = new HTTP()

const useDeleteSource = (slug) => {
    const result = ref(null)
    const error = ref(null)
    const loading = ref(true)

    const load = async () => {
        try {
            let url = `ui/v1/sources/${slug}`
            let response = await http.Delete(url)

            if (!response.result) {
                throw Error(response.errors?.[0] || 'Failed to delete source')
            } else {
                result.value = response.data
                loading.value = false
            }
        } catch (err) {
            error.value = err.message
            loading.value = false
        }
    }

    return { result, error, loading, load }
}

export default useDeleteSource
