import { ref } from 'vue'

const useDeleteSource = (slug) => {
    const result = ref(null)
    const error = ref(null)
    const loading = ref(true)

    const load = async () => {
        try {
            let url = `/ui/v1/sources/${slug}`
            let requestOptions = {
                method: 'DELETE',
                headers: {},
            }

            let response = await fetch(url, requestOptions)

            if (!response.ok) {
                throw Error(`failed to fetch ${response.url}. ${response.status}: ${response.statusText}`)
            } else {
                result.value = await response.json()
                loading.value = false
            }
        }
        catch (err) {
            error.value = err.message
            loading.value = false
        }
    }

    return { result, error, loading, load }
}

export default useDeleteSource
