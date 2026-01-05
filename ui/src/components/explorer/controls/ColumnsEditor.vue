<template>
    <div
        :style="{ height: `${editorHeight}px` }"
        class="editor border rounded-lg mt-1 border-neutral-300 pl-2 pr-2 dark:border-neutral-600"
        :class="{ 'border-sky-800 dark:border-sky-700': editorFocused }"
    >
        <vue-monaco-editor
            v-model:value="code"
            theme="telescope"
            language="columns"
            :options="getDefaultMonacoOptions()"
            @mount="handleMount"
            @change="onChange"
        />
    </div>
</template>

<script setup>
import { ref, computed, shallowRef, watch, onBeforeUnmount } from 'vue'

import * as monaco from 'monaco-editor'

import { Parser } from 'flyql/columns'
import { State } from 'flyql/columns/state'
import { MODIFIERS } from '@/utils/modifiers'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { getDefaultMonacoOptions } from '@/utils/monaco.js'

const emit = defineEmits(['change', 'submit'])
const props = defineProps(['source', 'value'])

const completionProvider = ref(null)

const editorFocused = ref(false)

const editorHeight = computed(() => {
    const lines = (code.value.match(/\n/g) || '').length + 1
    return 24 + lines * 20
})

const code = ref(props.value)
const editorRef = shallowRef()

const getExistingColumns = (text) => {
    const parser = new Parser()
    parser.parse(text, false, true)
    return parser.columns.map((c) => c.name)
}

const getColumnsNameSuggestions = (existingColumns, range) => {
    const suggestions = []
    for (const name of Object.keys(props.source.columns)) {
        if (props.source.columns[name].suggest) {
            if (!existingColumns.includes(name)) {
                suggestions.push({
                    label: name,
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    range: range,
                    insertText: name + ',',
                    command: {
                        id: 'editor.action.triggerSuggest',
                    },
                })
            }
        }
    }
    return suggestions
}

const getModifiersSuggestions = (range) => {
    const suggestions = []
    for (const name of Object.keys(MODIFIERS)) {
        suggestions.push({
            label: name,
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: name,
            range: range,
            command: {
                id: 'editor.action.triggerSuggest',
            },
        })
    }
    return suggestions
}

const getSuggestions = (word, range, textFull, textBeforeCursor) => {
    let suggestions = []
    const parser = new Parser()
    parser.parse(textBeforeCursor, false, true)
    if (parser.state == State.EXPECT_MODIFIER) {
        suggestions = getModifiersSuggestions(range)
    } else if (parser.state == State.MODIFIER) {
        if (!Object.keys(MODIFIERS).includes(word)) {
            suggestions = getModifiersSuggestions(range)
        }
    } else if (parser.state == State.EXPECT_COLUMN || parser.state == State.COLUMN) {
        suggestions = getColumnsNameSuggestions(getExistingColumns(textFull), range)
    }
    return suggestions
}

const handleMount = (editor) => {
    completionProvider.value = monaco.languages.registerCompletionItemProvider('columns', {
        provideCompletionItems: function (model, position) {
            let word = model.getWordUntilPosition(position)
            let range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn,
            }
            const textBeforeCursorRange = {
                startLineNumber: 1,
                endLineNumber: position.lineNumber,
                startColumn: 1,
                endColumn: position.column,
            }
            const textBeforeCursor = model.getValueInRange(textBeforeCursorRange)
            const textFull = model.getValue()
            const suggestions = getSuggestions(word.word, range, textFull, textBeforeCursor)
            return {
                suggestions: suggestions,
            }
        },
        triggerCharacters: [',', '|'],
    })
    editor.updateOptions({ placeholder: props.source.generateColumnsExample() })
    editorRef.value = editor
    editor.addAction({
        id: 'submit',
        label: 'submit',
        keybindings: [
            monaco.KeyMod.chord(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter),
            monaco.KeyMod.chord(monaco.KeyMod.Shift | monaco.KeyCode.Enter),
        ],
        run: (e) => {
            emit('submit')
        },
    })
    editor.addAction({
        id: 'triggerSugggest',
        label: 'triggerSuggest',
        keybindings: [monaco.KeyCode.Tab],
        run: (e) => {
            editor.trigger('triggerSuggest', 'editor.action.triggerSuggest', {})
        },
    })
    monaco.editor.addKeybindingRule({
        keybinding: monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyF,
        command: null,
    })
    editor.onDidFocusEditorWidget(() => {
        editorFocused.value = true
    })
    editor.onDidBlurEditorWidget(() => {
        editorFocused.value = false
    })
}
const onChange = () => {
    emit('change', code.value)
}

watch(props, () => {
    code.value = props.value
})

onBeforeUnmount(() => {
    completionProvider.value?.dispose()
})
</script>
