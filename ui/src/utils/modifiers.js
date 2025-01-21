function chars(value, from, to) {
    let args
    if (to === undefined) {
        args = [0, from]
    } else {
        args = [from, to]
    }
    return value.slice(...args)
}

function lines(value, from, to) {
    let args
    if (to === undefined) {
        args = [0, from]
    } else {
        args = [from, to]
    }
    return value.split(/\r?\n/).slice(...args).join('\n')
}

function slice(value, from, to) {
    let args = [from]
    if (to !== undefined) {
        args.push(to)
    }
    return value.slice(...args)
}

function firstline(value) {
    return value.split(/\r?\n/)[0]
}

function lastline(value) {
    let spl = value.split(/\r?\n/)
    return spl[spl.length - 1]
}

function oneline(value) {
    return value.replace(/(?:\r\n|\r|\n)/g, '')
}

function lower(value) {
    return value.toLowerCase()
}

function upper(value) {
    return value.toUpperCase()
}

function split(value, splitter) {
    return value.split(splitter)
}

function join(value, joiner) {
    return value.join(joiner)
}

function json(value) {
    return JSON.parse(value)
}

const MODIFIERS = {
    chars: chars,
    lines: lines,
    firstline: firstline,
    lastline: lastline,
    oneline: oneline,
    lower: lower,
    upper: upper,
    slice: slice,
    split: split,
    join: join,
    json: json,
}

export { MODIFIERS }