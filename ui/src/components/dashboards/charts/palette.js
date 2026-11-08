// Categorical order validated for adjacent-pair colorblind separation; red is kept for severity.
const CATEGORICAL = {
    light: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6'],
    dark: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9'],
}

const SEVERITY = {
    light: { fatal: '#b42318', error: '#e34948', warn: '#eda100', info: '#2a78d6', debug: '#8f8e88', trace: '#b9b8b2' },
    dark: { fatal: '#f97066', error: '#e5484d', warn: '#d4a017', info: '#3987e5', debug: '#8a8983', trace: '#5f5e59' },
}

// The one accent of single-color charts (top N bars, a lone series).
export const ACCENT = { light: '#2a78d6', dark: '#3987e5' }

const SEVERITY_LEVELS = {
    fatal: ['FATAL', 'PANIC', 'EMERGENCY', 'EMERG', 'CRIT', 'CRITICAL', 'ALERT'],
    error: ['ERROR', 'ERR', 'EXCEPTION', 'FAILURE'],
    warn: ['WARN', 'WARNING'],
    info: ['INFO', 'INFORMATION', 'INFORMATIONAL', 'NOTICE', 'AUDIT'],
    debug: ['DEBUG', 'VERBOSE'],
    trace: ['TRACE'],
}
const SEVERITY_ORDER = Object.keys(SEVERITY_LEVELS)
const LEVEL_OF = Object.fromEntries(
    Object.entries(SEVERITY_LEVELS).flatMap(([level, names]) => names.map((n) => [n, level])),
)

export const severityOf = (value) => LEVEL_OF[String(value ?? '').toUpperCase()]

// Severity coloring applies when the group-by names a level column or every group is a known level.
export const isSeverityGrouping = (groupBy, groups) => {
    const known = groups.filter((g) => g !== null && g !== undefined)
    if (!known.length) return false
    if (/(^|[._])(level|severity|lvl|loglevel)$/i.test(groupBy || '')) return known.some((g) => severityOf(g))
    return known.every((g) => severityOf(g))
}

export const severityRank = (value) => {
    const level = severityOf(value)
    return level ? SEVERITY_ORDER.indexOf(level) : SEVERITY_ORDER.length
}

export const severityColor = (value, theme) => {
    const level = severityOf(value)
    return level ? SEVERITY[theme][level] : null
}

// Series past the palette share one neutral, so no two of them look like the same entity.
const OTHER = { light: '#b9b8b2', dark: '#5f5e59' }

const hashOf = (text) => {
    let h = 2166136261
    for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619)
    return h >>> 0
}

// Each name starts at its own slot, so a service keeps its color across tiles, dashboards and traces.
// The first names in rank order get colors; a clash is settled by name, so the same pair always resolves alike.
export const entityColors = (names, theme) => {
    // Green is left out: next to aqua it reads as the same hue, and green marks logs in the trace view.
    const colors = CATEGORICAL[theme].filter((c) => c !== '#008300')
    const unique = [...new Set(names)]
    const result = new Map(unique.slice(colors.length).map((name) => [name, OTHER[theme]]))
    const taken = new Set()
    for (const name of unique.slice(0, colors.length).sort()) {
        let slot = hashOf(String(name)) % colors.length
        while (taken.has(slot)) slot = (slot + 1) % colors.length
        taken.add(slot)
        result.set(name, colors[slot])
    }
    return result
}

export const entityColor = (name, theme) => entityColors([name], theme).get(name)

export const categoricalColor = (index, theme) => {
    const colors = CATEGORICAL[theme]
    return colors[index % colors.length]
}
