function getDefaultIfUndefined(value, defaultValue) {
    if (value == undefined) {
        return defaultValue
    } else {
        return value
    }
}

function isNumeric(str) {
    if (typeof str != 'string') return false
    return !isNaN(str) && !isNaN(parseFloat(str))
}

function getBooleanFromString(value, defaultIfUndefined) {
    if (value == undefined) {
        return defaultIfUndefined
    } else {
        if (value.toLowerCase() === 'true') {
            return true
        } else {
            return false
        }
    }
}

export { getDefaultIfUndefined, isNumeric, getBooleanFromString }
