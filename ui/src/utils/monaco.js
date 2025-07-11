import * as monaco from 'monaco-editor'
import { loader } from '@guolao/vue-monaco-editor'

import { Parser as FieldsParser, tokenTypes as fieldsTokenTypes } from '@/utils/fields.js'
import { Parser as FlyqlParser, tokenTypes as flyqlTokenTypes, generateMonacoTokens } from 'flyql'

function getDefaultMonacoOptions() {
    return {
        readOnly: false,
        fontSize: 13,
        padding: {
            top: 20,
            bottom: 6,
        },
        contextmenu: false,
        tabCompletion: 'on',
        overviewRulerLanes: 0,
        lineNumbersMinChars: 0,
        scrollBeyondLastLine: false,
        scrollbarVisibility: 'hidden',
        scrollbar: {
            horizontal: 'hidden',
            vertical: 'hidden',
            alwaysConsumeMouseWheel: false,
            useShadows: false,
        },
        occurrencesHighlight: false,
        find: {
            addExtraSpaceOnTop: false,
            autoFindInSelection: 'never',
            seedSearchStringFromSelection: false,
        },
        wordBasedSuggestions: 'off',
        lineDecorationsWidth: 0,
        hideCursorInOverviewRuler: true,
        glyphMargin: false,
        scrollBeyondLastColumn: 0,
        automaticLayout: true,
        minimap: {
            enabled: false,
        },
        folding: false,
        lineNumbers: false,
        renderLineHighlight: 'none',
        matchBrackets: 'always',
        'semanticHighlighting.enabled': true,
    }
}

function initMonacoSetup() {
    loader.config({ monaco })
    monaco.editor.defineTheme('telescope', {
        base: 'vs',
        inherit: true,
        colors: {
            'editorGhostText.foreground': '#c6c6c6',
        },
        rules: [
            { token: 'field', foreground: '0451a5' },
            { token: 'alias', foreground: '0451a5', fontStyle: 'bold' },
            { token: 'operator', foreground: '0089ab' },
            { token: 'argument', foreground: '0451a5' },
            { token: 'modifier', foreground: '0089ab' },
            { token: 'error', foreground: 'ff0000' },
            { token: 'flyqlKey', foreground: '0451a5' },
            { token: 'flyqlOperator', foreground: '0089ab' },
            { token: 'flyqlValue', foreground: '8b0000' },

            { token: 'identifier', foreground: '0451a5' },
            { token: 'string.sql', foreground: '8b0000' },
            { token: 'operator.sql', foreground: '0089ab' },
        ],
    })
    monaco.editor.defineTheme('telescope-dark', {
        base: 'vs-dark',
        inherit: true,
        colors: {
            'editorGhostText.foreground': '#676767',
        },
        rules: [
            { token: 'field', foreground: '6e9fff' },
            { token: 'alias', foreground: '6e9fff', fontStyle: 'bold' },
            { token: 'operator', foreground: '0089ab' },
            { token: 'argument', foreground: 'ffffff' },
            { token: 'modifier', foreground: 'fa83f8' },
            { token: 'error', foreground: 'ff0000' },
            { token: 'flyqlKey', foreground: '6e9fff' },
            { token: 'flyqlOperator', foreground: '0089ab' },
            { token: 'flyqlValue', foreground: '8b0000' },

            { token: 'identifier', foreground: '6e9fff' },
            { token: 'string.sql', foreground: 'ce9178' },
            { token: 'operator.sql', foreground: '0089ab' },
        ],
    })
    monaco.languages.register({ id: 'fields' })
    monaco.languages.setLanguageConfiguration('fields', {
        autoClosingPairs: [{ open: '(', close: ')' }],
    })
    monaco.languages.registerDocumentSemanticTokensProvider('fields', {
        getLegend: () => ({
            tokenTypes: fieldsTokenTypes,
            tokenModifiers: [],
        }),
        provideDocumentSemanticTokens: (model) => {
            const parser = new FieldsParser()
            parser.parse(model.getValue())

            const data = parser.generateMonacoTokens()

            return {
                data: new Uint32Array(data),
                resultId: null,
            }
        },
        releaseDocumentSemanticTokens: () => {},
    })

    monaco.languages.register({ id: 'flyql' })
    monaco.languages.registerDocumentSemanticTokensProvider('flyql', {
        getLegend: () => ({
            tokenTypes: flyqlTokenTypes,
            tokenModifiers: [],
        }),
        provideDocumentSemanticTokens: (model) => {
            const parser = new FlyqlParser()
            parser.parse(model.getValue(), false)
            const data = generateMonacoTokens(parser)
            return {
                data: new Uint32Array(data),
                resultId: null,
            }
        },
        releaseDocumentSemanticTokens: () => {},
    })
}

export { initMonacoSetup, getDefaultMonacoOptions }
