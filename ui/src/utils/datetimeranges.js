import { DateTime } from 'luxon'

const absoluteTimeFormat = 'yyyy-MM-dd HH:mm:ss.SSS'
const relativeTimeRegex = new RegExp('^now(?:-(?<value>[0-9]+)(?<unit>[dhms]))?$')

export const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
export const availableTimeZones = Intl.supportedValuesOf('timeZone')

// Workaround for some engines not including UTC in this list
if (!availableTimeZones.map((tz) => tz.toLowerCase()).some((tz) => tz === 'etc/utc' || tz === 'utc'))
    availableTimeZones.push('UTC')

export const relativeTimeRanges = [
    { label: 'Last 1 minute', from: 'now-1m', to: 'now' },
    { label: 'Last 5 minutes', from: 'now-5m', to: 'now' },
    { label: 'Last 15 minutes', from: 'now-15m', to: 'now' },
    { label: 'Last 30 minutes', from: 'now-30m', to: 'now' },
    { label: 'Last 1 hour', from: 'now-1h', to: 'now' },
    { label: 'Last 2 hours', from: 'now-2h', to: 'now' },
    { label: 'Last 6 hours', from: 'now-6h', to: 'now' },
    { label: 'Last 12 hours', from: 'now-12h', to: 'now' },
    { label: 'Last 24 hours', from: 'now-24h', to: 'now' },
]

export function tryGetRelativeOption(from, to) {
    return relativeTimeRanges.filter((opt) => opt.from === from && opt.to === to)[0] ?? null
}

export function getNiceRangeText(from, to, timeZone) {
    if (typeof from === 'string' && typeof to === 'string')
        return tryGetRelativeOption(from, to)?.label ?? `${from} - ${to}`

    return `${getDateTimeString(from, timeZone)} - ${getDateTimeString(to, timeZone)}`
}

export function moveTimestampToTimeZone(timestamp, oldTimeZone, newTimeZone) {
    if (typeof timestamp !== 'number') return timestamp

    const oldTzTime = DateTime.fromMillis(timestamp, { zone: oldTimeZone })
    const newTzTime = oldTzTime.setZone(newTimeZone, { keepLocalTime: true })
    return newTzTime.toMillis()
}

export function getDateTimeString(input, timeZone) {
    if (typeof input !== 'number') return input

    return DateTime.fromMillis(input, { zone: timeZone }).toFormat(absoluteTimeFormat)
}

export function tryParseDateTimeString(input, timeZone) {
    if (relativeTimeRegex.test(input)) return { result: input, error: null }

    const parsedTime = DateTime.fromFormat(input, absoluteTimeFormat, { zone: timeZone })
    if (parsedTime.isValid) return { result: parsedTime.toMillis(), error: null }

    if (parsedTime.invalidReason === 'unparsable')
        return {
            result: null,
            error: `Expected absolute (${absoluteTimeFormat}) or relative (${relativeTimeRegex}) time`,
        }

    const luxonErr = parsedTime.invalidExplanation
    return { result: null, error: luxonErr.charAt(0).toUpperCase() + luxonErr.slice(1) }
}
