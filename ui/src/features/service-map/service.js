import { ref } from 'vue'
import HTTP from '@/utils/http'

const http = new HTTP()

const errorText = (response) => {
    if (response.errors?.length) return response.errors.join(', ')
    const v = response.validation || {}
    const fields = Object.entries(v.fields || {}).map(([k, e]) => `${k}: ${[].concat(e).join(' ')}`)
    return [...(v.non_field || []), ...fields].join(', ') || 'invalid request'
}

// Service map data for one traces source; a new load aborts the previous one.
export const useServiceMap = () => {
    const data = ref(null)
    const error = ref(null)
    const loading = ref(false)
    let controller = null

    const load = async (slug, body) => {
        controller?.abort()
        controller = new AbortController()
        const signal = controller.signal
        loading.value = true
        const response = await http.Post(`ui/v1/otel/${slug}/serviceMap`, body, signal)
        if (signal.aborted) return
        data.value = response.result ? response.data : null
        error.value = response.result ? null : errorText(response)
        loading.value = false
    }
    return { data, error, loading, load }
}
