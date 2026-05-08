import { ColumnSchema } from 'flyql'
import { parse as parseColumnsExpr } from 'flyql/columns'
import { normalizeClickHouseType } from 'flyql/generators/clickhouse'
import { normalizeStarRocksType } from 'flyql/generators/starrocks'

const _COLUMN_NAMES_CAPS = { transformers: true, renderers: true }

/**
 * Extract bare column names from a columns-input string. Used by `Row.vue`
 * to list the currently displayed columns. Delegates to flyql's columns
 * parser so quoting, escapes, and transformer/alias syntax stay in lockstep
 * with the editor.
 *
 * Mid-edit input (a half-typed transformer chain, trailing comma, etc.)
 * makes the strict parser throw. To avoid flickering Row.vue's "selected
 * columns" indicator while the user types, we retry against truncated
 * prefixes that lop off the in-progress trailing token before giving up.
 * On unrecoverable input we return `[]`.
 */
export function parseColumnNames(text) {
    if (!text || !text.trim()) return []
    // Truncation candidates, longest-first: full text, then prefix up to
    // the last pipe (typing a transformer), then up to the last comma
    // (typing a new column). Each is tried only if it strictly extends
    // the previous attempt's coverage.
    const candidates = [text]
    const lastPipe = text.lastIndexOf('|')
    if (lastPipe > 0) candidates.push(text.slice(0, lastPipe))
    const lastComma = text.lastIndexOf(',')
    if (lastComma > 0 && lastComma > lastPipe) {
        candidates.push(text.slice(0, lastComma))
    }
    for (const candidate of candidates) {
        try {
            return parseColumnsExpr(candidate, _COLUMN_NAMES_CAPS).map((c) => c.name)
        } catch {
            // try next candidate
        }
    }
    return []
}

/**
 * Build a flyql `ColumnSchema` from a Telescope `Source`.
 * Consumed by `<FlyqlEditor>` / `<FlyqlColumns>` via the `:columns` prop,
 * which feeds it directly into flyql-vue's `ColumnsEngine`/`EditorEngine`.
 *
 * Column types are normalized to canonical flyql `Type.*` tokens via the
 * dialect normalizer for the source's kind, so the editor surface (operator
 * filtering, suggestion detail column) sees the flyql vocabulary instead of
 * raw DB type strings like `Nullable(String)` or `DateTime64(3)`.
 *
 * Container types (`json`, `jsonstring`, `map`) are downgraded to `'object'`
 * (which normalizes to `Type.Unknown`) so flyql-vue treats them as schemaless
 * and triggers `onKeyDiscovery` for nested-key autocomplete — see
 * `docs.flyql.dev/editor/schema` "Schemaless objects".
 */
const _CONTAINER_TYPES = new Set(['json', 'jsonstring', 'map'])

export function buildFlyqlColumnSchema(source) {
    const plain = {}
    if (!source || !source.columns) return ColumnSchema.fromPlainObject(plain)
    const normalize = _typeNormalizerFor(source.kind)
    for (const [name, col] of Object.entries(source.columns)) {
        const normalized = col.jsonstring ? 'jsonstring' : normalize(col.type)
        const finalType = _CONTAINER_TYPES.has(normalized) ? 'object' : normalized
        plain[name] = {
            type: finalType,
            display_name: col.display_name || '',
            suggest: col.suggest !== undefined ? col.suggest : true,
            autocomplete: col.autocomplete !== undefined ? col.autocomplete : true,
            values: Array.isArray(col.values) ? col.values : [],
        }
    }
    return ColumnSchema.fromPlainObject(plain)
}

function _typeNormalizerFor(kind) {
    if (kind === 'clickhouse') return normalizeClickHouseType
    if (kind === 'starrocks') return normalizeStarRocksType
    // kubernetes and docker fetchers already emit canonical flyql tokens
    // ('string', 'datetime', 'json', ...) — pass through unchanged.
    return (t) => t
}
