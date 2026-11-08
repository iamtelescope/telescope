import { parseColumnNames } from '@/sdk/flyql'

// Edits of the FlyQL columns string ("a, b as x, c|upper") by column name, keeping each entry's own text.
export function splitColumns(text) {
    const parts = []
    let quote = null
    let depth = 0
    let start = 0
    for (let i = 0; i < (text || '').length; i++) {
        const ch = text[i]
        if (quote) {
            if (ch === '\\') i++
            else if (ch === quote) quote = null
        } else if (ch === "'" || ch === '"') quote = ch
        else if (ch === '(') depth++
        else if (ch === ')') depth = Math.max(0, depth - 1)
        else if (ch === ',' && depth === 0) {
            parts.push(text.slice(start, i))
            start = i + 1
        }
    }
    parts.push((text || '').slice(start))
    return parts.map((p) => p.trim()).filter((p) => p)
}

const nameOf = (entry) => parseColumnNames(entry)[0] ?? entry

export function hasColumn(text, name) {
    return splitColumns(text).some((entry) => nameOf(entry) === name)
}

export function removeColumn(text, name) {
    const parts = splitColumns(text)
    const index = parts.findIndex((entry) => nameOf(entry) === name)
    if (index >= 0) parts.splice(index, 1)
    return parts.join(', ')
}

export function addColumn(text, name) {
    return [...splitColumns(text), name].join(', ')
}

// Swaps two columns, e.g. a header and its visible neighbour.
export function swapColumns(text, a, b) {
    const parts = splitColumns(text)
    const i = parts.findIndex((entry) => nameOf(entry) === a)
    const j = parts.findIndex((entry) => nameOf(entry) === b)
    if (i >= 0 && j >= 0) [parts[i], parts[j]] = [parts[j], parts[i]]
    return parts.join(', ')
}
