import { ref } from 'vue'

const usePatchSource = () => {
    const result = ref(null)
    const error = ref(null)
    const loading = ref(true)

    const load = async (slug, data) => {
        try {
            let url = `/ui/v1/sources/${slug}`
            let requestOptions = {
                method: 'PATCH',
                headers: {},
                body: JSON.stringify(data)   
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

export default usePatchSource
