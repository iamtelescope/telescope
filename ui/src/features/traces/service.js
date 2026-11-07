import { ref } from 'vue'
import HTTP from '@/utils/http'

const http = new HTTP()

const post = (slug, path, traceId, aroundMs, signal) =>
    http.Post(`ui/v1/otel/${slug}/${path}`, { trace_id: traceId, around_ms: aroundMs ?? null }, signal)

// Loads one endpoint's data; a new load aborts the previous one.
const useTraceRequest = (path) => {
    const data = ref(null)
    const error = ref(null)
    const loading = ref(false)
    let controller = null

    const load = async (slug, traceId, aroundMs) => {
        controller?.abort()
        controller = new AbortController()
        const signal = controller.signal
        loading.value = true
        const response = await post(slug, path, traceId, aroundMs, signal)
        if (signal.aborted) return
        data.value = response.result ? response.data : null
        error.value = response.result ? null : response.errors.join(', ') || 'invalid request'
        loading.value = false
    }
    return { data, error, loading, load }
}

export const useTrace = () => useTraceRequest('trace')
export const useTraceLogs = () => useTraceRequest('traceLogs')
