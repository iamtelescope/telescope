import { useDark } from '@vueuse/core'

import { entityColor, severityColor } from '@/components/dashboards/charts/palette.js'

const isDark = useDark()
export const currentTheme = () => (isDark.value ? 'dark' : 'light')

// Syslog numbers and a few other names map onto the dashboards' severity palette.
const ALIASES = {
    0: 'FATAL',
    O: 'FATAL',
    1: 'ERROR',
    2: 'ERROR',
    3: 'ERROR',
    4: 'WARN',
    5: 'INFO',
    6: 'DEBUG',
    7: 'TRACE',
    CONFIG: 'INFO',
    NORMAL: 'INFO',
}

// The level name a severity value stands for (syslog numbers included), or the value itself.
export const levelOf = (value) => {
    const key = String(value).toUpperCase()
    return ALIASES[key] ?? key
}

// Severity values use the severity palette; any other value gets its own categorical color.
function getColor(value) {
    const theme = currentTheme()
    return severityColor(levelOf(value), theme) || entityColor(String(value), theme)
}

function getContrastColor(backgroundColor) {
    backgroundColor = backgroundColor.replace(/^#/, '')

    let r = parseInt(backgroundColor.substr(0, 2), 16)
    let g = parseInt(backgroundColor.substr(2, 2), 16)
    let b = parseInt(backgroundColor.substr(4, 2), 16)

    let luma = 0.2126 * r + 0.7152 * g + 0.0722 * b

    return luma > 150 ? 'black' : 'white'
}

export { getColor, getContrastColor }
