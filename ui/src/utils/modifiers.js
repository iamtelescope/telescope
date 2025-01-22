function chars(value, from, to) {
    let args
    try {
        if (to === undefined) {
            args = [0, from]
        } else {
            args = [from, to]
        }
        return value.slice(...args)
    } catch (e) {
        return value
    }

}

function lines(value, from, to) {
    let args
    try {
        if (to === undefined) {
            args = [0, from]
        } else {
            args = [from, to]
        }
        return value.split(/\r?\n/).slice(...args).join('\n')
    } catch (e) {
        return value
    }

}

function slice(value, from, to) {
    let args = [from]
    try {
        if (to !== undefined) {
            args.push(to)
        }
        return value.slice(...args)
    } catch (e) {
        return value
    }

}

function firstline(value) {
    try {
        return value.split(/\r?\n/)[0]
    } catch (e) {
        return value
    }

}

function lastline(value) {
    try {
        let spl = value.split(/\r?\n/)
        return spl[spl.length - 1]
    } catch (e) {
        return value
    }

}

function oneline(value) {
    try {
        return value.replace(/(?:\r\n|\r|\n)/g, '')
    } catch (e) {
        return value
    }

}

function lower(value) {
    try {
        return value.toLowerCase()
    } catch (e) {
        return value
    }

}

function upper(value) {
    try {
        return value.toUpperCase()
    } catch (e) {
        return value
    }

}

function split(value, splitter) {
    try {
        return value.split(splitter)
    } catch (e) {
        return value
    }

}

function join(value, joiner) {
    try {
        return value.join(joiner)
    } catch (e) {
        return value
    }

}

function json(value) {
    try {
        return JSON.parse(value)
    } catch (e) {
        return value
    }
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