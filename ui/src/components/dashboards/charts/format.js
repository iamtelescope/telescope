// Labels, units and number formatting shared by the dashboard chart renderers.
const LOCALE = 'en-US'

export const seriesLabel = (s) => {
    if (!s) return 'value'
    if (s.alias) return s.alias
    if (s.agg === 'count') return 'count'
    if (s.agg === 'quantile') return `p${Math.round((s.level || 0) * 100)} ${s.column}`
    return `${s.agg} ${s.column}`
}

// The title of a single-value tile, e.g. "count of rows" or "p95 duration_ms".
export const valueLabel = (s) => (s && !s.alias && s.agg === 'count' ? 'count of rows' : seriesLabel(s))

export const groupLabel = (group) => (group === '__none__' || group === '' ? '(empty)' : String(group))

// An explicit tile unit wins; with the default "number" the unit is guessed from the column name.
export const seriesUnit = (s, numberFormat) => {
    const unit = numberFormat?.unit
    if (unit && unit !== 'number') return unit
    if (!s || !s.column || s.agg === 'count' || s.agg === 'uniq') return 'number'
    const col = s.column.toLowerCase()
    if (/(_ms$|duration|latency|elapsed)/.test(col)) return 'duration_ms'
    if (/(bytes|_size$|^size$)/.test(col)) return 'bytes'
    return 'number'
}

const fixed = (v, digits) =>
    v.toLocaleString(LOCALE, { minimumFractionDigits: 0, maximumFractionDigits: Math.max(0, digits) })

// Up to 3 significant digits: 1.23, 12.3, 123.
const short = (v) => {
    const abs = Math.abs(v)
    return fixed(v, abs >= 100 ? 0 : abs >= 10 ? 1 : 2)
}

const scaled = (v, base, units, fmt) => {
    let i = 0
    while (Math.abs(v) >= base && i < units.length - 1) {
        v /= base
        i++
    }
    return `${fmt(v)} ${units[i]}`
}

const duration = (v, fmt) => {
    const abs = Math.abs(v)
    if (abs < 1000) return `${fmt(v)} ms`
    if (abs < 60000) return `${fmt(v / 1000)} s`
    if (abs < 3600000) return `${fmt(v / 60000)} min`
    if (abs < 86400000) return `${fmt(v / 3600000)} h`
    return `${fmt(v / 86400000)} d`
}

// compact: 1.2K / 3.4M style for tiles and axes; otherwise plain numbers honor the tile decimals.
export const formatNumber = (value, unit = 'number', { compact = false, decimals } = {}) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '–'
    const fmt = compact || decimals === undefined ? short : (v) => fixed(v, decimals)
    // Scaled units keep 3 significant digits so "1.5 s" never rounds to "2 s".
    if (unit === 'bytes') return scaled(value, 1024, ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'], short)
    if (unit === 'duration_ms') return duration(value, short)
    if (unit === 'percent') return `${fmt(value)}%`
    if (compact && Math.abs(value) >= 1000) {
        return value.toLocaleString(LOCALE, { notation: 'compact', maximumSignificantDigits: 3 })
    }
    if (compact) return short(value)
    return decimals === undefined ? value.toLocaleString(LOCALE, { maximumFractionDigits: 2 }) : fixed(value, decimals)
}

// Full-precision text for title attributes.
export const exactNumber = (value) =>
    value === null || value === undefined ? '' : value.toLocaleString(LOCALE, { maximumFractionDigits: 6 })
