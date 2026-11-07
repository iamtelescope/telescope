import { localTimeZone } from '@/utils/datetimeranges'

export const TIMESERIES_DISPLAYS = ['line', 'stacked_area', 'stacked_bar']

export const DISPLAYS = [
    { value: 'line', label: 'Line' },
    { value: 'stacked_area', label: 'Area' },
    { value: 'stacked_bar', label: 'Bars' },
    { value: 'number', label: 'Number' },
    { value: 'table', label: 'Table' },
    { value: 'bar', label: 'Top N' },
    { value: 'text', label: 'Text' },
]

export const AGGS = ['count', 'sum', 'avg', 'min', 'max', 'quantile', 'uniq']
export const QUANTILE_LEVELS = [0.5, 0.75, 0.9, 0.95, 0.99]
export const GRANULARITIES = ['auto', '15s', '30s', '1m', '5m', '10m', '15m', '30m', '1h', '2h', '6h', '12h', '1d']
export const REFRESH_OPTIONS = ['off', '30s', '1m', '5m']
export const REFRESH_MS = { '30s': 30000, '1m': 60000, '5m': 300000 }
export const NUMBER_UNITS = ['number', 'bytes', 'duration_ms', 'percent']
export const MAX_SERIES = 5

export const isTimeseries = (display) => TIMESERIES_DISPLAYS.includes(display)
export const maxLimit = (display) => (isTimeseries(display) ? 50 : 100)

// Spec section 5 numeric type check, after unwrapping Nullable and LowCardinality.
export const isNumericType = (type) => {
    let t = String(type || '')
    let prev = null
    while (prev !== t) {
        prev = t
        t = t.replace(/^\s*(Nullable|LowCardinality)\((.*)\)\s*$/i, '$2')
    }
    return (
        /^(U?Int\d+|Float\d+|Decimal.*)$/.test(t) ||
        /^(tinyint|smallint|int|bigint|largeint|float|double|decimal.*)$/i.test(t)
    )
}

export const countOnlyKind = (kind) => kind === 'docker' || kind === 'kubernetes'

export const emptyDashboardData = () => ({
    time: { from: 'now-1h', to: 'now', time_zone: localTimeZone },
    query: '',
    refresh: 'off',
    tiles: [],
})

export const newTileId = (tiles) => {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    const used = new Set((tiles || []).map((t) => t.id))
    let id
    do {
        id = Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
    } while (used.has(id))
    return id
}

export const defaultTileSize = (display) =>
    display === 'number' || display === 'text' ? { w: 6, h: 4 } : { w: 12, h: 8 }

export const bottomY = (tiles) => Math.max(0, ...(tiles || []).map((t) => t.y + t.h))

export const formatValue = (value, format) => {
    if (value === null || value === undefined) return '–'
    const unit = format?.unit || 'number'
    const decimals = format?.decimals ?? (unit === 'number' ? undefined : 2)
    const num = (v) =>
        v.toLocaleString(
            undefined,
            decimals === undefined ? {} : { minimumFractionDigits: decimals, maximumFractionDigits: decimals },
        )
    const scaled = (v, base, units) => {
        let i = 0
        while (Math.abs(v) >= base && i < units.length - 1) {
            v /= base
            i++
        }
        return `${num(v)} ${units[i]}`
    }
    if (unit === 'bytes') return scaled(value, 1024, ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'])
    if (unit === 'percent') return `${num(value)}%`
    if (unit === 'duration_ms') {
        const abs = Math.abs(value)
        if (abs < 1000) return `${num(value)} ms`
        if (abs < 60000) return `${num(value / 1000)} s`
        if (abs < 3600000) return `${num(value / 60000)} min`
        return `${num(value / 3600000)} h`
    }
    return num(value)
}
