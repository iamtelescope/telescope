const MAX_VALUE = 10000
const limitValues = [50, 100, 500, 1000, 2000, 5000, MAX_VALUE]

function getLimits(selected) {
    if (selected < 1) {
        selected = 1
    } else if (selected > MAX_VALUE) {
        selected = MAX_VALUE
    }
    let values = new Set(limitValues)
    values.add(selected)
    let limits = []
    for (let value of values) {
        limits.push(value)
    }
    return limits
}

export { getLimits }
