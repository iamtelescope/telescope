import { format, parse, isValid } from 'date-fns'

const dateTimeFormat = 'yyyy-MM-dd HH:mm:ss.SSS'

const humanRelatedTimeRegex = new RegExp('^now(?:-(?<value>[0-9]+)(?<unit>[dhms]))?$')

const datetimeRanges = {
    'Last 1 minute': {
        'from': 'now-1m',
        'to': 'now',
    },
    'Last 5 minutes': {
        'from': 'now-5m',
        'to': 'now',
    },
    'Last 15 minutes': {
        'from': 'now-15m',
        'to': 'now',
    },
    'Last 30 minutes': {
        'from': 'now-30m',
        'to': 'now',
    },
    'Last 1 hour': {
        'from': 'now-1h',
        'to': 'now',
    },
    'Last 2 hours': {
        'from': 'now-2h',
        'to': 'now',
    },
    'Last 6 hours': {
        'from': 'now-6h',
        'to': 'now',
    },
    'Last 12 hours': {
        'from': 'now-12h',
        'to': 'now',
    },
    'Last 24 hours': {
        'from': 'now-24h',
        'to': 'now',
    }
}

const datetimeRangesReversed = {}

for (const key in datetimeRanges) {
    let from = datetimeRanges[key].from
    let to = datetimeRanges[key].to
    datetimeRangesReversed[`${from} - ${to}`] = key
}

function getRelativeOption(from, to) {
    let key = `${from} - ${to}`
    let text = datetimeRangesReversed[key]
    if (text) {
        return { "label": text, 'from': from, 'to': to }
    } else {
        return null
    }
}

function getRelativeOptions() {
    let options = []
    for (const key in datetimeRanges) {
        options.push({ 'label': key, 'from': datetimeRanges[key].from, 'to': datetimeRanges[key].to })
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
        result.parsed = true
    } else {
        let intValue = parseInt(value)
        if (!isNaN(intValue)) {
            result.parsed = true
            result.date = new Date(intValue)
        } else {
            result.date = parse(value, dateTimeFormat, new Date())
            result.parsed = isValid(result.date)
            if (!result.parsed) {
                if (humanRelatedTimeRegex.exec(value)) {
                    result.relative = true
                }
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
        return fmt(new Date(intValue))
    }
    // value is str date like '2024-12-12 00:00:00.000'
    const parsedDate = parse(value, dateTimeFormat, new Date())
    if (isValid(parsedDate)) {
        return fmt(parsedDate)
    }
    // invalid value
    return null
}

function fmt(date) {
    return format(date, dateTimeFormat)
}

function getDatetimeRangeText(from, to) {
    let key = `${from} - ${to}`
    let text = datetimeRangesReversed[key]
    if (text) {
        return text
    } else {
        let fromResult = getDateIfTimestamp(from)
        let toResult = getDateIfTimestamp(to)
        if (fromResult.parsed) {
            from = fmt(fromResult.date)
        }
        if (toResult.parsed) {
            to = fmt(toResult.date)
        }
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

export { datetimeRanges, dateTimeFormat, humanRelatedTimeRegex, getStrDateOrStrRelative, getDatetimeRangeText, getRelativeOption, getRelativeOptions, getDateIfTimestamp, fmt, dateIsValid }