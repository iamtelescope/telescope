import { format } from 'date-fns'

const datetimeRanges = {
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
        date: value,
    }
    if (value instanceof Date) {
        result.parsed = true
    } else {
        let intValue = parseInt(value)
        if (!isNaN(intValue)) {
            result.parsed = true
            result.date = new Date(intValue)
        }
    }
    return result
}

function fmt(date) {
    return format(date, 'yyyy-MM-dd HH:mm:ss')
}

function getDatetimeRangeText(from, to) {
    let key = `${from} - ${to}`
    let text = datetimeRangesReversed[key]
    if (text) {
        return text
    } else {
        let fromResult = getDateIfTimestamp(from)
        let toResult = getDateIfTimestamp(to)
        if (fromResult.parsed && toResult.parsed) {
            from = fmt(fromResult.date)
            to = fmt(toResult.date)
            return `${from} - ${to}`
        } else {
            return key
        }
    }
}

export { datetimeRanges, getDatetimeRangeText, getRelativeOption, getRelativeOptions, getDateIfTimestamp, fmt }