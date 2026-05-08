import he from 'he'
import hljs from 'highlight.js'
import { format as sqlformat } from 'sql-formatter'
import { ArgSpec, Renderer, RendererRegistry, Transformer, TransformerRegistry, Type } from 'flyql'

const SQL_KEYWORDS = new Set([
    'select',
    'insert',
    'update',
    'create',
    'grant',
    'revoke',
    'alter',
    'drop',
    'begin',
    'commit',
    'rollback',
    'with',
    'explain',
    'show',
    'set',
    'start',
])

function detectLang(value) {
    if (value && typeof value === 'object') {
        return 'json'
    }
    if (typeof value !== 'string') {
        return undefined
    }
    const trimmed = value.trimStart()
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        return 'json'
    }
    let firstWord = ''
    for (const ch of trimmed) {
        if (ch === ' ' || ch === '\n' || ch === '\t' || ch === '\r') {
            break
        }
        firstWord += ch.toLowerCase()
    }
    if (SQL_KEYWORDS.has(firstWord)) {
        return 'sql'
    }
    return undefined
}

function uiOnly(name) {
    throw new Error(`transformer '${name}' is UI-only and cannot be used in queries`)
}

// -- Transformers -----------------------------------------------------------

class CharsTransformer extends Transformer {
    get name() {
        return 'chars'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    get argSchema() {
        return [new ArgSpec(Type.Int, true), new ArgSpec(Type.Int, false)]
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value, args = []) {
        if (value == null) return value
        if (!args.length) return value
        try {
            if (args.length >= 2) {
                return String(value).slice(Number(args[0]), Number(args[1]))
            }
            return String(value).slice(0, Number(args[0]))
        } catch (_e) {
            return value
        }
    }
}

class LinesTransformer extends Transformer {
    get name() {
        return 'lines'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    get argSchema() {
        return [new ArgSpec(Type.Int, true), new ArgSpec(Type.Int, false)]
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value, args = []) {
        if (value == null) return value
        if (!args.length) return value
        try {
            const lines = String(value).split(/\r?\n/)
            if (args.length >= 2) {
                return lines.slice(Number(args[0]), Number(args[1])).join('\n')
            }
            return lines.slice(0, Number(args[0])).join('\n')
        } catch (_e) {
            return value
        }
    }
}

class FirstlineTransformer extends Transformer {
    get name() {
        return 'firstline'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value) {
        if (value == null) return value
        try {
            return String(value).split(/\r?\n/)[0]
        } catch (_e) {
            return value
        }
    }
}

class LastlineTransformer extends Transformer {
    get name() {
        return 'lastline'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value) {
        if (value == null) return value
        try {
            const spl = String(value).split(/\r?\n/)
            return spl[spl.length - 1]
        } catch (_e) {
            return value
        }
    }
}

class OnelineTransformer extends Transformer {
    get name() {
        return 'oneline'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value) {
        if (value == null) return value
        try {
            return String(value).replace(/(?:\r\n|\r|\n)/g, '')
        } catch (_e) {
            return value
        }
    }
}

class LowerTransformer extends Transformer {
    get name() {
        return 'lower'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    sql(dialect, columnRef) {
        if (dialect === 'starrocks') return `LOWER(${columnRef})`
        return `lower(${columnRef})`
    }
    apply(value) {
        if (value == null) return value
        try {
            return String(value).toLowerCase()
        } catch (_e) {
            return value
        }
    }
}

class UpperTransformer extends Transformer {
    get name() {
        return 'upper'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    sql(dialect, columnRef) {
        if (dialect === 'starrocks') return `UPPER(${columnRef})`
        return `upper(${columnRef})`
    }
    apply(value) {
        if (value == null) return value
        try {
            return String(value).toUpperCase()
        } catch (_e) {
            return value
        }
    }
}

class SliceTransformer extends Transformer {
    get name() {
        return 'slice'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    get argSchema() {
        return [new ArgSpec(Type.Int, true), new ArgSpec(Type.Int, false)]
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value, args = []) {
        if (value == null) return value
        try {
            if (args.length >= 2) return value.slice(Number(args[0]), Number(args[1]))
            return value.slice(Number(args[0]))
        } catch (_e) {
            return value
        }
    }
}

class SplitTransformer extends Transformer {
    get name() {
        return 'split'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.Array
    }
    get argSchema() {
        return [new ArgSpec(Type.String, false)]
    }
    sql(dialect, columnRef, args = []) {
        const delimiter = args[0] || ','
        const escaped = "'" + String(delimiter).replace(/[\\']/g, (ch) => '\\' + ch) + "'"
        if (dialect === 'clickhouse') {
            if (String(delimiter).length === 1) return `splitByChar(${escaped}, ${columnRef})`
            return `splitByString(${escaped}, ${columnRef})`
        }
        if (dialect === 'starrocks') return `SPLIT(${columnRef}, ${escaped})`
        return `STRING_TO_ARRAY(${columnRef}, ${escaped})`
    }
    apply(value, args = []) {
        if (value == null) return value
        const delimiter = args[0] !== undefined ? String(args[0]) : ','
        try {
            return String(value).split(delimiter)
        } catch (_e) {
            return value
        }
    }
}

class JoinTransformer extends Transformer {
    get name() {
        return 'join'
    }
    get inputType() {
        return Type.Array
    }
    get outputType() {
        return Type.String
    }
    get argSchema() {
        return [new ArgSpec(Type.String, false)]
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value, args = []) {
        if (!Array.isArray(value)) return value
        const joiner = args[0] !== undefined ? String(args[0]) : ','
        try {
            return value.join(joiner)
        } catch (_e) {
            return value
        }
    }
}

class JsonTransformer extends Transformer {
    get name() {
        return 'json'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.Unknown
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value) {
        if (value == null) return value
        try {
            return typeof value === 'string' ? JSON.parse(value) : value
        } catch (_e) {
            return value
        }
    }
}

class StrTransformer extends Transformer {
    get name() {
        return 'str'
    }
    get inputType() {
        return Type.Unknown
    }
    get outputType() {
        return Type.String
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value) {
        if (value == null) return value
        try {
            if (typeof value === 'object') return JSON.stringify(value)
            return String(value)
        } catch (_e) {
            return value
        }
    }
}

class TypeTransformer extends Transformer {
    get name() {
        return 'type'
    }
    get inputType() {
        return Type.Unknown
    }
    get outputType() {
        return Type.String
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value) {
        if (value === null) return 'null'
        if (Array.isArray(value)) return 'array'
        return typeof value
    }
}

class FmtTransformer extends Transformer {
    get name() {
        return 'fmt'
    }
    get inputType() {
        return Type.String
    }
    get outputType() {
        return Type.String
    }
    get argSchema() {
        return [new ArgSpec(Type.String, false)]
    }
    sql() {
        return uiOnly(this.name)
    }
    apply(value, args = []) {
        if (value == null) return value
        let lang = args[0]
        if (!lang) lang = detectLang(value)
        if (!lang) return value
        try {
            if (lang === 'sql') return sqlformat(String(value), { language: 'sql' })
            if (lang === 'json') {
                const parsed = typeof value === 'object' ? value : JSON.parse(value)
                return JSON.stringify(parsed, null, 4)
            }
        } catch (_e) {
            return value
        }
        return value
    }
}

class FormatTransformer extends FmtTransformer {
    get name() {
        return 'format'
    }
}

// -- Renderers --------------------------------------------------------------

class HighlightRenderer extends Renderer {
    get name() {
        return 'highlight'
    }
    get argSchema() {
        return [new ArgSpec(Type.String, false)]
    }
    get metadata() {
        return { output: 'html' }
    }

    render(value, args = []) {
        let v = value
        if (typeof v === 'object') v = JSON.stringify(v)
        const lang = args[0] || detectLang(v)
        if (!lang) return v
        return hljs.highlight(String(v), { language: lang }).value
    }
}

class HlRenderer extends HighlightRenderer {
    get name() {
        return 'hl'
    }
}

class HrefRenderer extends Renderer {
    get name() {
        return 'href'
    }
    get argSchema() {
        return [new ArgSpec(Type.String, true), new ArgSpec(Type.String, false)]
    }
    get metadata() {
        return { output: 'html' }
    }

    render(value, args = []) {
        if (value == null || value === '') return value
        const template = args[0] || ''
        const urlValue = args[1] === undefined ? String(value) : String(args[1])
        const url = template.replace('${value}', String(value))
        if (!/^[a-zA-Z0-9]+?:\/\//.test(url)) return he.encode(String(value))
        return `<a class="text-primary hover:underline hover:cursor-pointer" href="${he.encode(url)}" target="_blank" title="${he.encode(url)}">${he.encode(urlValue)}</a>`
    }
}

// -- Registry builders ------------------------------------------------------

function buildTransformerRegistry() {
    const registry = new TransformerRegistry()
    registry.register(new CharsTransformer())
    registry.register(new LinesTransformer())
    registry.register(new FirstlineTransformer())
    registry.register(new LastlineTransformer())
    registry.register(new OnelineTransformer())
    registry.register(new LowerTransformer())
    registry.register(new UpperTransformer())
    registry.register(new SliceTransformer())
    registry.register(new SplitTransformer())
    registry.register(new JoinTransformer())
    registry.register(new JsonTransformer())
    registry.register(new StrTransformer())
    registry.register(new TypeTransformer())
    registry.register(new FmtTransformer())
    registry.register(new FormatTransformer())
    return registry
}

function buildRendererRegistry() {
    const registry = new RendererRegistry()
    registry.register(new HighlightRenderer())
    registry.register(new HlRenderer())
    registry.register(new HrefRenderer())
    registry.setDiagnose((parsedColumn) => {
        const renderers = parsedColumn?.renderers || []
        if (renderers.length > 1) {
            return [
                {
                    code: 'RENDERER_CHAIN_NOT_ALLOWED',
                    message: 'at most one renderer per column',
                },
            ]
        }
        return []
    })
    return registry
}

export const transformerRegistry = buildTransformerRegistry()
export const rendererRegistry = buildRendererRegistry()

// -- Pipeline helpers -------------------------------------------------------

/**
 * Apply transformers then at most one renderer to a raw cell value.
 * Returns { value, isHtml }. Null/undefined values skip transformers and
 * receive `""` for the renderer stage. An exception in any apply/render call
 * aborts the pipeline for that row and returns the raw value.
 */
export function applyColumnPipeline(column, value) {
    const transformers = column.transformers || []
    const renderers = column.renderers || []

    let current = value
    const isNullish = current === null || current === undefined

    if (!isNullish) {
        for (const t of transformers) {
            const impl = transformerRegistry.get(t.name)
            if (!impl) {
                return { value, isHtml: false }
            }
            try {
                current = impl.apply(current, t.arguments || [])
            } catch (_e) {
                return { value, isHtml: false }
            }
        }
    } else {
        current = ''
    }

    if (renderers.length === 0) {
        return { value: current, isHtml: false }
    }

    const renderer = renderers[0]
    const impl = rendererRegistry.get(renderer.name)
    if (!impl || typeof impl.render !== 'function') {
        return { value: current, isHtml: false }
    }
    try {
        return { value: impl.render(current, renderer.arguments || []), isHtml: true }
    } catch (_e) {
        return { value, isHtml: false }
    }
}
