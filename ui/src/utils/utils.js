function getDefaultIfUndefined(value, default_value) {
    if (value == undefined) {
        return default_value;
    } else {
        return value
    }
}

export { getDefaultIfUndefined }