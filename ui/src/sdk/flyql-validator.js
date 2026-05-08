/**
 * Client-side FlyQL validator. Runs the same `parse` + `diagnose` flow that
 * the backend runs, so obviously-broken queries/columns are caught before we
 * hit the server and save a round-trip.
 *
 * Backend validation is still authoritative (RBAC, fetcher failures, schema
 * drift); this is a pre-filter, never a replacement.
 */

import { CODE_UNKNOWN_COLUMN, diagnose as diagnoseQueryFn, parse as parseQuery } from 'flyql'
import { diagnose as diagnoseColumnsFn, parse as parseColumns } from 'flyql/columns'

import { buildFlyqlColumnSchema } from '@/sdk/flyql'
import { rendererRegistry, transformerRegistry } from '@/utils/flyql-registries'

const COLUMNS_CAPABILITIES = { transformers: true, renderers: true }

// Backend's parse_columns suppresses unknown-column diagnostics because
// Telescope resolves dotted paths against the source schema with richer
// semantics than flyql's segment walker — mirror that suppression here so
// the pre-flight UI validator and the server stay in sync.
const COLUMN_NOT_DEFINED_CODES = new Set([CODE_UNKNOWN_COLUMN])

// flyql exposes diagnose() with positional args (JS has no kwargs). Pin the
// signature here so a future flyql release that inserts a parameter only
// needs to be reconciled in this one place — see version pin in package.json.
//
// flyql/core (query):    diagnose(ast, schema, registry?)
// flyql/columns (cols):  diagnose(parsedColumns, schema, registry?, rendererRegistry?)
function diagnoseQuery(ast, schema) {
    return diagnoseQueryFn(ast, schema, transformerRegistry)
}

function diagnoseColumns(parsedColumns, schema) {
    return diagnoseColumnsFn(parsedColumns, schema, transformerRegistry, rendererRegistry)
}

function _parseErrorDiagnostic(err, text, section) {
    return {
        section,
        input: text,
        message: err?.message || String(err) || 'parse error',
        range: err?.range || null,
        code: err?.code || 'parse_error',
        severity: 'error',
    }
}

function _validateColumns(schema, text) {
    if (!text || !text.trim()) return []
    let parsed
    try {
        parsed = parseColumns(text, COLUMNS_CAPABILITIES)
    } catch (err) {
        return [_parseErrorDiagnostic(err, text, 'columns')]
    }
    const diags = diagnoseColumns(parsed, schema)
    return diags
        .filter((d) => d.severity === 'error' && !COLUMN_NOT_DEFINED_CODES.has(d.code))
        .map((d) => ({ ...d, section: 'columns', input: text }))
}

function _validateQuery(schema, text) {
    if (!text || !text.trim()) return []
    let parser
    try {
        parser = parseQuery(text)
    } catch (err) {
        return [_parseErrorDiagnostic(err, text, 'query')]
    }
    // Degenerate inputs (e.g. text that produces zero AST nodes) can
    // surface a parser with a null root. flyql's diagnose treats the null
    // case as undefined behavior, so short-circuit to no diagnostics.
    if (!parser || !parser.root) return []
    const diags = diagnoseQuery(parser.root, schema)
    return diags.filter((d) => d.severity === 'error').map((d) => ({ ...d, section: 'query', input: text }))
}

/**
 * Validate the FlyQL columns + query strings for a given source.
 *
 * Returns `{ valid: boolean, diagnostics: Diagnostic[] }`. Each diagnostic
 * carries the original `range`, `message`, `code`, `severity` from flyql
 * plus two convenience fields:
 *   - `section`: 'query' | 'columns' — which input the diagnostic came from.
 *   - `input`:   the original string, so the view can render the offending span.
 */
export function validateFlyqlInputs(source, { query, columns }) {
    const schema = buildFlyqlColumnSchema(source)
    const diagnostics = [..._validateColumns(schema, columns), ..._validateQuery(schema, query)]
    return { valid: diagnostics.length === 0, diagnostics }
}
