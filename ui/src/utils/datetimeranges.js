import { format, parse, isValid } from 'date-fns'
import { DateTime } from 'luxon'

const dateTimeFormat = 'yyyy-MM-dd HH:mm:ss.SSS'

const humanRelatedTimeRegex = new RegExp('^now(?:-(?<value>[0-9]+)(?<unit>[dhms]))?$')

const datetimeRanges = {
    'Last 1 minute': {
        from: 'now-1m',
        to: 'now',
    },
    'Last 5 minutes': {
        from: 'now-5m',
        to: 'now',
    },
    'Last 15 minutes': {
        from: 'now-15m',
        to: 'now',
    },
    'Last 30 minutes': {
        from: 'now-30m',
        to: 'now',
    },
    'Last 1 hour': {
        from: 'now-1h',
        to: 'now',
    },
    'Last 2 hours': {
        from: 'now-2h',
        to: 'now',
    },
    'Last 6 hours': {
        from: 'now-6h',
        to: 'now',
    },
    'Last 12 hours': {
        from: 'now-12h',
        to: 'now',
    },
    'Last 24 hours': {
        from: 'now-24h',
        to: 'now',
    },
}

const datetimeRangesReversed = {}

for (const key in datetimeRanges) {
    let from = datetimeRanges[key].from
    let to = datetimeRanges[key].to
    datetimeRangesReversed[`${from} - ${to}`] = key
}

class TelescopeDate {
    constructor(data) {
        this.value = data.value
        this.timezone = data.timezone
        this.isRelative = false
        this.dateObj = null
        this.strValue = null
        this.error = ''
        try {
            if (humanRelatedTimeRegex.exec(this.value)) {
                this.isRelative = true
                this.strValue = this.value
            } else {
                this.dateObj = DateTime.fromMillis(parseInt(this.value), { zone: this.timezone })
                this.strValue = this.dateObj.toFormat(dateTimeFormat)
            }
        } catch (e) {
            this.error = `failed to initialize date: ${e.toTostring()}`
        }
    }
}

function getRelativeOption(from, to) {
    let key = `${from} - ${to}`
    let text = datetimeRangesReversed[key]
    if (text) {
        return { label: text, from: from, to: to }
    } else {
        return null
    }
}

function getRelativeOptions() {
    let options = []
    for (const key in datetimeRanges) {
        options.push({ label: key, from: datetimeRanges[key].from, to: datetimeRanges[key].to })
    }
    return options
}

function getDateIfTimestamp(value) {
    let result = {
        parsed: false,
        relative: false,
        date: value,
    }
    if (value instanceof Date) {
        result.value = DateTime.fromJSDate(value).setZone('UTC')
        result.parsed = true
    } else {
        let intValue = parseInt(value)
        if (!isNaN(intValue)) {
            result.parsed = true
            result.date = DateTime.fromMillis(intValue, { zone: 'UTC' })
        } else {
            result.date = parse(value, dateTimeFormat, new Date())

            result.parsed = isValid(result.date)
            if (!result.parsed) {
                if (humanRelatedTimeRegex.exec(value)) {
                    result.relative = true
                }
            } else {
                result.date = DateTime.fromJSDate(result.date).setZone('UTC')
            }
        }
    }
    return result
}

function getStrDateOrStrRelative(value) {
    // value is date obj
    if (value instanceof Date) {
        return fmt(value)
    }
    // value is relative like 'now-1h'
    if (humanRelatedTimeRegex.exec(value)) {
        return value
    }
    // value is int timestamp

    const intValue = parseInt(value)
    if (!isNaN(intValue)) {
        return DateTime.fromMillis(intValue, { zone: 'UTC' }).toFormat(dateTimeFormat)
    }
    // value is str date like '2024-12-12 00:00:00.000'
    const parsedDate = parse(value, dateTimeFormat, new Date())
    if (isValid(parsedDate)) {
        return DateTime.fromJSDate(parsedDate).setZone('UTC').toFormat(dateTimeFormat)
    }
    // invalid value
    return null
}

function fmt(date) {
    return format(date, dateTimeFormat)
}

function getDatetimeRangeText(from, to) {
    // Accepts TelescopeDate obj
    let key = `${from} - ${to}`
    let text = datetimeRangesReversed[key]
    if (text) {
        return text
    } else {
        return `${from} - ${to}`
    }
}

function dateIsValid(dateString) {
    let parsedDate = parse(dateString, dateTimeFormat, new Date())
    let valid = isValid(parsedDate)
    if (!valid) {
        if (humanRelatedTimeRegex.exec(dateString)) {
            valid = true
            parsedDate = dateString
        }
    }

    return [parsedDate, valid]
}

export {
    TelescopeDate,
    datetimeRanges,
    dateTimeFormat,
    humanRelatedTimeRegex,
    getStrDateOrStrRelative,
    getDatetimeRangeText,
    getRelativeOption,
    getRelativeOptions,
    getDateIfTimestamp,
    fmt,
    dateIsValid,
}
