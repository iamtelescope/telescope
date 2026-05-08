import * as monaco from 'monaco-editor'
import { loader } from '@guolao/vue-monaco-editor'

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
            { token: 'identifier', foreground: '6e9fff' },
            { token: 'string.sql', foreground: 'ce9178' },
            { token: 'operator.sql', foreground: '0089ab' },
        ],
    })
}

export { initMonacoSetup, getDefaultMonacoOptions }
