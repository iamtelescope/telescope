function getDefaultIfUndefined(value, default_value) {
    if (value == undefined) {
        return default_value;
    } else {
        return value
    }
}

function isNumeric(str) {
    if (typeof str != "string") return false
    return !isNaN(str) &&
        !isNaN(parseFloat(str))
}

export { getDefaultIfUndefined, isNumeric }