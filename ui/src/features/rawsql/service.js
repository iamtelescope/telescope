import getCSRFToken from '@/utils/csrf'
import UIResponse from '@/sdk/models/response'
import { useChartData } from '@/composables/dashboards/useDashboardService'

// Like utils/http, but a 403 still carries the JSON envelope with its `no_access` code.
const request = async (url, method, body, signal) => {
    const response = new UIResponse()
    try {
        const headers = { Accept: 'application/json', 'Content-Type': 'application/json' }
        if (method === 'POST') headers['X-CSRFToken'] = getCSRFToken()
        const r = await fetch(url, { method, headers, signal, body: body && JSON.stringify(body) })
        if (!r.ok && r.status !== 403) throw Error(`failed to fetch ${r.url}. ${r.status}: ${r.statusText}`)
        // A CSRF failure or an expired session answers with an HTML page.
        const data = await r.json().catch(() => {
            throw Error(
                `Invalid JSON response from ${r.url} (${r.status}). Your session may have expired: reload the page.`,
            )
        })
        Object.assign(response, {
            result: data.result,
            data: data.data,
            errors: data.errors || [],
            messages: data.messages || [],
            validation: data.validation,
        })
    } catch (err) {
        if (err.name === 'AbortError') return null
        response.result = false
        response.errors = [err.message]
    }
    return response
}

export const rawSqlConnections = () => request('ui/v1/rawsql/connections', 'GET')

export const runRawSql = (connection, body, signal, attribution) => {
    const qs = attribution ? `?${new URLSearchParams(attribution)}` : ''
    return request(`ui/v1/rawsql/connections/${connection}/query${qs}`, 'POST', body, signal)
}

export const rawSqlBody = (chart, range) => ({
    from: range.from,
    to: range.to,
    sql: chart.sql || '',
    granularity: chart.granularity || 'auto',
    params: range.params || {},
})

// useChartData that also runs raw SQL tiles, into the same refs.
export const useTileData = (queue, attribution) => {
    const chart = useChartData(queue, attribution)
    let controller = null
    const abort = () => {
        controller?.abort()
        controller = null
        chart.abort()
    }
    const load = async (target, body, display) => {
        abort()
        if (display !== 'sql') return chart.load(target, body)
        const current = new AbortController()
        controller = current
        chart.loading.value = true
        const call = () => runRawSql(target, body, current.signal, attribution?.())
        const response = queue ? await queue(call, current.signal) : await call()
        if (current.signal.aborted || !response) return
        chart.data.value = response.result ? response.data : null
        chart.error.value = response.errors.join(', ')
        chart.code.value = response.result ? null : response.data?.code || null
        chart.validation.value = response.validation
        chart.loading.value = false
        controller = null
    }
    return { ...chart, load, abort }
}

export const RAW_SQL_EXAMPLE = `SELECT $__timeInterval(event_time) AS t, count() AS queries
FROM system.query_log
WHERE $__timeFilter(event_time)
GROUP BY t
ORDER BY t DESC`

export const MACROS = [
    ['$__timeFilter(col)', 'col within the dashboard range'],
    ['$__fromTime, $__toTime', 'range start and end, DateTime'],
    ['$__interval_s', 'granularity in seconds'],
    ['$__timeInterval(col)', 'col bucketed to the granularity'],
    ['{name:String}', 'dashboard variable, bound as a parameter'],
]
