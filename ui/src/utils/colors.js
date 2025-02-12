const UNKNOWN = "#d568fb"
const FATAL = "#e3554c"
const ERROR = FATAL
const WARN = "#edb359"
const INFO = "#9bcce4"
const DEBUG = "#60ac53"
const TRACE = "#009aa3"

const colors = ["#2caffe", "#544fc5", "#00e272", "#fe6a35", "#6b8abc", "#2ee0ca", UNKNOWN, FATAL, WARN, INFO, DEBUG, TRACE]

const severityColors = {
    UNKNOWN: UNKNOWN,
    FATAL: FATAL,
    ERROR: ERROR,
    WARN: WARN,
    WARNING: WARN,
    INFO: INFO,
    DEBUG: DEBUG,
    TRACE: TRACE,
    EMERGENCY: FATAL,
    VERBOSE: TRACE,
    AUDIT: INFO,
    SUCCESS: DEBUG,
    OK: DEBUG,
    FAILURE: ERROR,
    PANIC: FATAL,
    EXCEPTION: FATAL,
    CRIT: FATAL,
    CRITICAL: ERROR,
    CONFIG: INFO,
    INFORMATIONAL: INFO,
    NOTICE: INFO,
    NORMAL: INFO,
    "O": FATAL,
    "1": ERROR,
    "2": ERROR,
    "3": ERROR,
    "4": WARN,
    "5": INFO,
    "6": DEBUG,
    "7": TRACE,
}

function colorGenerator() {
    let index = 0
    const data = {}
    return function (value) {
        let color = data[value]
        if (color === undefined) {
            color = colors[index]
            index = (index + 1) % colors.length
            data[value] = color
        }
        return color
    }
}

const getNextColor = colorGenerator()

function getColor(value) {
    let color = severityColors[String(value).toUpperCase()]
    if (color === undefined) {
        color = getNextColor(value)
    }
    return color
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