import { ref } from 'vue'
import HTTP from '@/utils/http'

const http = new HTTP()

// Aggregations per metric type; mirrors backend telescope_otel/metrics_sql.py METRIC_AGGS.
const QUANTILES = ['p50', 'p90', 'p95', 'p99']
const GAUGE = ['avg', 'min', 'max', 'last']
export const METRIC_AGGS = {
    gauge: GAUGE,
    sum: ['rate', 'increase', ...GAUGE],
    histogram: QUANTILES,
    exponential_histogram: QUANTILES,
    summary: QUANTILES,
}
export const METRIC_TYPE_LABELS = {
    gauge: 'gauge',
    sum: 'sum',
    histogram: 'histogram',
    exponential_histogram: 'exp histogram',
    summary: 'summary',
}
export const METRIC_AGG_LABELS = { rate: 'rate /s', increase: 'increase', last: 'last value' }

export const isMetricsSource = (source) => !!source?.otel?.metric_tables && source.otelSignal === 'metrics'

export const defaultMetricAgg = (type) => METRIC_AGGS[type]?.[type === 'histogram' ? 2 : 0] || 'avg'

export const metricLabel = (metric) => `${metric?.agg || '…'}(${metric?.name || '…'})`

// A FlyQL condition on an attribute path such as `Attributes.http.route`.
export const attributeFilter = (path, value) => {
    const [column, ...key] = path.split('.')
    return `${column}.'${key.join('.').replace(/'/g, "\\'")}' = '${String(value).replace(/'/g, "\\'")}'`
}

// Loads one catalog endpoint; a new load aborts the previous one.
const useCatalog = (path, pick) => {
    const data = ref(pick(null))
    const error = ref(null)
    const loading = ref(false)
    let controller = null

    const load = async (slug, body) => {
        controller?.abort()
        controller = new AbortController()
        const signal = controller.signal
        loading.value = true
        const response = await http.Post(`ui/v1/otel/${slug}/metrics/${path}`, body, signal)
        if (signal.aborted) return
        data.value = pick(response.result ? response.data : null)
        error.value = response.result ? null : response.errors.join(', ') || 'invalid request'
        loading.value = false
    }
    return { data, error, loading, load }
}

export const useMetricNames = () => useCatalog('names', (d) => d?.metrics || [])
export const useMetricAttributes = () => useCatalog('attributes', (d) => d?.keys || [])
export const useAttributeValues = () => useCatalog('attributes', (d) => d?.values || [])
