import { DateTime } from 'luxon'

// One place for how dates read in the UI. Values: ISO string, epoch ms, Date or luxon DateTime.
export const toDateTime = (value, zone) => {
    if (value === null || value === undefined || value === '') return null
    let dt
    if (DateTime.isDateTime(value)) dt = value
    else if (value instanceof Date) dt = DateTime.fromJSDate(value)
    else if (typeof value === 'number') dt = DateTime.fromMillis(value)
    else dt = DateTime.fromISO(String(value))
    if (!dt.isValid) return null
    return zone ? dt.setZone(zone) : dt
}

// "2026-11-07 14:03:12 UTC"; { ms: true } adds milliseconds, { zone: false } drops the zone name.
export const formatDateTime = (value, { zone, ms = false, withZone = true, empty = '—' } = {}) => {
    const dt = toDateTime(value, zone)
    if (!dt) return empty
    return dt.toFormat(`yyyy-MM-dd HH:mm:ss${ms ? '.SSS' : ''}${withZone ? ' ZZZZ' : ''}`)
}

// "5 minutes ago", "in 2 hours".
export const formatRelative = (value, { empty = '—' } = {}) => toDateTime(value)?.toRelative() ?? empty

// 950 -> "950 ms", 1500 -> "1.5 s", 125000 -> "2m 5s".
export const formatDuration = (ms) => {
    if (ms === null || ms === undefined || Number.isNaN(ms)) return '—'
    if (ms < 1000) return `${Math.round(ms * 100) / 100} ms`
    if (ms < 60_000) return `${Math.round(ms / 100) / 10} s`
    const s = Math.round(ms / 1000)
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    return h ? `${h}h ${m}m` : `${m}m ${s % 60}s`
}
