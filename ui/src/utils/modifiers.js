import he from "he"
import hljs from "highlight.js"
import { format as sqlformat } from "sql-formatter"

const SQLKeyWords = ['select', 'insert', 'update', 'create', 'grant', 'revoke', 'alter', 'drop', 'begin', 'commit', 'rollback', 'with', 'explain', 'show', 'set', 'start']


function mod_chars(value, from, to) {
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

function mod_lines(value, from, to) {
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

function mod_slice(value, from, to) {
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

function mod_firstline(value) {
    try {
        return value.split(/\r?\n/)[0]
    } catch (e) {
        return value
    }
}

function mod_lastline(value) {
    try {
        let spl = value.split(/\r?\n/)
        return spl[spl.length - 1]
    } catch (e) {
        return value
    }
}

function mod_oneline(value) {
    try {
        return value.replace(/(?:\r\n|\r|\n)/g, '')
    } catch (e) {
        return value
    }
}

function mod_lower(value) {
    try {
        return value.toLowerCase()
    } catch (e) {
        return value
    }
}

function mod_upper(value) {
    try {
        return value.toUpperCase()
    } catch (e) {
        return value
    }
}

function mod_split(value, splitter) {
    try {
        return value.split(splitter)
    } catch (e) {
        return value
    }
}

function mod_join(value, joiner) {
    try {
        return value.join(joiner)
    } catch (e) {
        return value
    }
}

function mod_json(value) {
    try {
        return JSON.parse(value)
    } catch (e) {
        return value
    }
}

function mod_str(value) {
    try {
        if (typeof (value) === 'object') {
            return JSON.stringify(value)
        } else {
            return String(value)
        }
    } catch (e) {
        return value
    }
}

function mod_type(value) {
    try {
        return typeof (value)
    } catch (e) {
        return value
    }
}

function detectLang(value) {
    let language
    if (typeof (value) === 'object') {
        return 'json'
    }
    if (value.startsWith('{') || value.startsWith('[')) {
        language = 'json'
    } else {
        let first_word = ''
        for (const char of value) {
            if (char != ' ' && char != '\n') {
                first_word += char.toLowerCase()
            } else {
                break
            }
        }
        if (first_word.length > 0 && SQLKeyWords.includes(first_word)) {
            language = 'sql'
        }

    }
    return language
}

function mod_fmt(value, language) {
    if (language === undefined) {
        language = detectLang(value)
        if (language === undefined) {
            return value
        }
    }
    try {
        if (language == 'sql') {
            return sqlformat(value, { language: "sql" });
        } else if (language == 'json') {
            if (typeof (value) === 'object') {
                return JSON.stringify(value, '', 4)
            } else {
                return JSON.stringify(JSON.parse(value), '', 4)
            }
        }

    } catch (e) {
        return value
    }
}

function mod_href(value, urlTemplate, urlValue) {
    if (!value) {
        return value;
    }
    try {
        if (urlValue === undefined) {
            urlValue = value
        }

        const safeValue = he.encode(value)
        const safeUrlValue = he.encode(urlValue)

        let url = urlTemplate.replace('${value}', safeValue)
        if (!/^[a-zA-Z0-9]+?:\/\//.test(url)) {
            return safeValue
        }
        return `<a class="text-prm hover:underline" href="${he.encode(url)}" target="_blank" title="${he.encode(url)}">${safeUrlValue}</a>`
    } catch (e) {
        return value
    }
}

function mod_highlight(value, language) {
    try {
        if (typeof (value) === 'object') {
            value = JSON.stringify(value)
        }
        if (language === undefined) {
            language = detectLang(value)
            if (language === undefined) {
                return value
            }
        }
        return hljs.highlight(value, { language: language }).value
    } catch (e) {

        return value
    }
}


const MODIFIERS = {
    chars: { func: mod_chars, type: 'value' },
    lines: { func: mod_lines, type: 'value' },
    firstline: { func: mod_firstline, type: 'value' },
    lastline: { func: mod_lastline, type: 'value' },
    oneline: { func: mod_oneline, type: 'value' },
    lower: { func: mod_lower, type: 'value' },
    upper: { func: mod_upper, type: 'value' },
    slice: { func: mod_slice, type: 'value' },
    split: { func: mod_split, type: 'value' },
    join: { func: mod_join, type: 'value' },
    json: { func: mod_json, type: 'value' },
    str: { func: mod_str, type: 'value' },
    type: { func: mod_type, type: 'value' },
    fmt: { func: mod_fmt, type: 'value' },
    format: { func: mod_fmt, type: 'value' },

    hl: { func: mod_highlight, type: 'html' },
    highlight: { func: mod_highlight, type: 'html' },
    href: { func: mod_href, type: 'html' },

}

export { MODIFIERS }