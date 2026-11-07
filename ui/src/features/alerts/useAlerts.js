// Shared alert vocabulary; threshold types and intervals follow HyperDX common-utils/src/types.ts (MIT).
export const INTERVALS = ['1m', '5m', '15m', '30m', '1h', '6h', '12h', '1d']

export const THRESHOLD_TYPES = [
    { value: 'above', label: 'at or above', symbol: '≥' },
    { value: 'above_exclusive', label: 'above', symbol: '>' },
    { value: 'below', label: 'below', symbol: '<' },
    { value: 'below_or_equal', label: 'at or below', symbol: '≤' },
    { value: 'equal', label: 'equal to', symbol: '=' },
    { value: 'not_equal', label: 'not equal to', symbol: '≠' },
    { value: 'between', label: 'between', symbol: 'between' },
    { value: 'not_between', label: 'outside', symbol: 'outside' },
]

export const isRange = (type) => type === 'between' || type === 'not_between'

export const STATE_SEVERITY = {
    OK: 'success',
    ALERT: 'danger',
    PENDING: 'warn',
    INSUFFICIENT_DATA: 'secondary',
    ERROR: 'danger',
    DISABLED: 'secondary',
}

export const STATE_LABEL = {
    OK: 'OK',
    ALERT: 'Firing',
    PENDING: 'Pending',
    INSUFFICIENT_DATA: 'No data',
    ERROR: 'Error',
    DISABLED: 'Disabled',
}

export const CHANNEL_KINDS = [
    { value: 'slack', label: 'Slack', icon: 'pi pi-comments' },
    { value: 'webhook', label: 'Webhook', icon: 'pi pi-link' },
    { value: 'pagerduty', label: 'PagerDuty', icon: 'pi pi-bell' },
    { value: 'email', label: 'Email', icon: 'pi pi-envelope' },
]

const fmt = (v) =>
    v === null || v === undefined ? '' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 6 })

export const describeSeries = (s) => {
    if (!s || !s.agg) return ''
    if (s.agg === 'count') return 'count()'
    if (s.agg === 'quantile') return `p${Math.round(s.level * 100)}(${s.column})`
    return `${s.agg}(${s.column})`
}

export const describeCondition = (alert) => {
    const t = THRESHOLD_TYPES.find((x) => x.value === alert.threshold_type)
    if (!t) return ''
    if (isRange(alert.threshold_type)) return `${t.symbol} ${fmt(alert.threshold)} and ${fmt(alert.threshold_max)}`
    return `${t.symbol} ${fmt(alert.threshold)}`
}

// Validation errors of a UIResponse as one line.
export const responseProblem = (response) => {
    const flat = (value, key) => {
        if (Array.isArray(value)) return value.map((v) => flat(v)).join(', ')
        if (value && typeof value === 'object')
            return Object.entries(value)
                .map(([k, v]) => flat(v, k))
                .join('; ')
        return key ? `${key}: ${value}` : String(value)
    }
    const fields = response.validation?.fields || {}
    const parts = [...(response.errors || []), ...(response.validation?.non_field || [])]
    for (const [key, value] of Object.entries(fields)) parts.push(`${key}: ${flat(value)}`)
    return parts.join('; ')
}
