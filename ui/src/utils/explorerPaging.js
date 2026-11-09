// Explorer helpers for load more, live tail, bare-text search and CSV export (P1.2).

import getCSRFToken from '@/utils/csrf'

export const LIVE_INTERVALS = [2, 5, 10]
export const LIVE_MAX_ROWS = 5000
const TEXT_SEARCH_KINDS = ['clickhouse', 'starrocks']
const BODY_COLUMN_NAMES = ['body', 'message', 'msg', 'log']
const RELATIVE_TIME = /^now(?:-(\d+)([dhms]))?$/
const UNIT_MS = { d: 86400000, h: 3600000, m: 60000, s: 1000 }

// Same rule as backend telescope/fetchers/search.py body_column().
export function bodyColumn(source) {
    if (!source || !TEXT_SEARCH_KINDS.includes(source.kind)) return null
    const columns = source.columns || {}
    const otel = source.data?.otel || {}
    const role = otel.roles?.body || otel.body
    if (role && role in columns) return role
    const byLower = Object.fromEntries(Object.keys(columns).map((name) => [name.toLowerCase(), name]))
    for (const name of BODY_COLUMN_NAMES) {
        if (byLower[name]) return byLower[name]
    }
    return null
}

export function supportsPaging(source) {
    return !!source && TEXT_SEARCH_KINDS.includes(source.kind)
}

// Relative times ('now-5m') as ms at nowMs, so later pages keep the window of the first one.
export function resolveTime(value, nowMs) {
    if (typeof value === 'number') return value
    const match = RELATIVE_TIME.exec(value)
    if (!match) return value
    return match[1] ? nowMs - parseInt(match[1]) * UNIT_MS[match[2]] : nowMs
}

export function rowKey(row) {
    return `${row.time.unixtime}.${row.time.microseconds}|${JSON.stringify(row.data)}`
}

// Prepends a live poll to the shown rows; rows at the poll's lower bound may already be shown.
export function mergeLiveRows(rows, fresh, boundary, max = LIVE_MAX_ROWS) {
    const seen = new Set(rows.filter((r) => r.time.unixtime >= boundary).map(rowKey))
    const added = fresh.filter((r) => !seen.has(rowKey(r)))
    const merged = added.concat(rows)
    return { rows: merged.slice(0, max), added: added.length, trimmed: merged.length > max }
}

// Value of a (possibly segmented) column in a row's data, walking flyql's parsed segments.
export function columnValue(column, data) {
    if (!column.is_segmented) return data[column.root_name]
    let segments = column.segments
    if (!segments || segments.length === 0) {
        segments = column.name ? column.name.split('.') : []
    }
    let cur = data
    for (let i = 0; i < segments.length; i++) {
        if (cur === null || typeof cur !== 'object') return undefined
        const seg = segments[i]
        if (!(seg in cur)) {
            // A dotted top-level name (e.g. `container.id`) lives flat in `data`.
            if (i === 0) {
                const rejoined = segments.join('.')
                if (rejoined in cur) return cur[rejoined]
            }
            return undefined
        }
        cur = cur[seg]
    }
    return cur
}

function csvField(value) {
    let text
    if (value === null || value === undefined) text = ''
    else if (typeof value === 'object') text = JSON.stringify(value)
    else text = String(value)
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function rowTimeISO(row) {
    return `${row.time.datetime.replace(' ', 'T')}.${row.time.microseconds}Z`
}

// RFC 4180: CRLF line ends, fields with quotes, commas or line breaks quoted and quotes doubled.
export function toCsv(columns, rows) {
    const header = ['Time', ...columns.map((c) => c.name)]
    const lines = [header.map(csvField).join(',')]
    for (const row of rows) {
        lines.push([rowTimeISO(row), ...columns.map((c) => columnValue(c, row.data))].map(csvField).join(','))
    }
    return lines.join('\r\n') + '\r\n'
}

export function downloadFile(content, type, filename) {
    const blob = new Blob([content], { type })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}

// Posts a form into a hidden frame, so the browser streams the response to disk as a download.
// A download never loads the frame; a load is an error page, whose text goes to onError.
export function postDownload(url, params, onError) {
    const frame = document.createElement('iframe')
    frame.name = `download-${Date.now()}-${Math.random().toString(36).slice(2)}`
    frame.style.display = 'none'
    document.body.appendChild(frame)
    frame.addEventListener('load', () => {
        let text = ''
        try {
            if (frame.contentWindow.location.href === 'about:blank') return
            text = frame.contentDocument?.body?.textContent || ''
        } catch (err) {}
        onError(text)
        frame.remove()
    })
    const form = document.createElement('form')
    form.method = 'POST'
    form.action = url
    form.target = frame.name
    const fields = { params: JSON.stringify(params), csrfmiddlewaretoken: getCSRFToken() || '' }
    for (const [name, value] of Object.entries(fields)) {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = name
        input.value = value
        form.appendChild(input)
    }
    document.body.appendChild(form)
    form.submit()
    form.remove()
}
