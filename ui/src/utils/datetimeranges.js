import { format, parse, isValid } from 'date-fns'

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

function fmt(date) {
    return format(date, dateTimeFormat)
}

function getNiceRangeText(from, to, timeZone) {
    if (typeof(from) === 'string' && typeof(to) === 'string') {
        const rangeString = `${from} - ${to}`
        if (rangeString in datetimeRangesReversed)
            return datetimeRangesReversed[rangeString]
        else
            return rangeString
    }

    const dateTimeFormat = Intl.DateTimeFormat('en-GB', {
        dateStyle: 'short',
        hour12: false,
        timeStyle: 'short',
        timeZone
    })

    if (typeof(from) === 'number' && typeof(to) === 'number')
        return dateTimeFormat.formatRange(new Date(from), new Date(to))

    const formatSingle = (input) => {
        if (typeof(input) === 'string')
            return input
        else
            return dateTimeFormat.format(new Date(input))
    }
    return `${formatSingle(from)} - ${formatSingle(to)}`
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
    datetimeRanges,
    dateTimeFormat,
    humanRelatedTimeRegex,
    getNiceRangeText,
    getRelativeOption,
    getRelativeOptions,
    fmt,
    dateIsValid,
}
