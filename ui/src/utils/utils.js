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

// Flattens nested server validation errors to {'a.b.0.c': ['message']}.
function flattenFieldErrors(fields, prefix = '') {
    const result = {}
    for (const [key, value] of Object.entries(fields || {})) {
        const name = key === 'non_field_errors' && prefix ? prefix : prefix ? `${prefix}.${key}` : key
        if (Array.isArray(value) && value.every((v) => v === null || typeof v !== 'object')) {
            result[name] = [...(result[name] || []), ...value.map(String)]
        } else if (value && typeof value === 'object') {
            for (const [k, v] of Object.entries(flattenFieldErrors(value, name))) {
                result[k] = [...(result[k] || []), ...v]
            }
        } else {
            result[name] = [...(result[name] || []), String(value)]
        }
    }
    return result
}

function fieldErrorsText(fields) {
    return Object.entries(flattenFieldErrors(fields))
        .map(([k, v]) => `${k}: ${v.join(', ')}`)
        .join('; ')
}

export { getDefaultIfUndefined, isNumeric, getBooleanFromString, flattenFieldErrors, fieldErrorsText }
