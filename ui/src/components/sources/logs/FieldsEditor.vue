<template>
    <div :style="{ height: `${editorHeight}px` }" class="editor border rounded mt-1 pl-2 pr-2 mb-2"
        :class="{ 'border-sky-800': editorFocused }">
        <vue-monaco-editor v-model:value="code" theme="telescope" language="fields" :options="getDefaultMonacoOptions()"
            @mount="handleMount" @change="onChange" />
    </div>
</template>s

<script setup>
import { ref, computed, shallowRef } from 'vue'

import * as monaco from 'monaco-editor'

import { Parser, State, CHARS } from '@/utils/fields.js'
import { MODIFIERS } from '@/utils/modifiers'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { getDefaultMonacoOptions } from '@/utils/monaco.js'

const emit = defineEmits(['change', 'submit',])
const props = defineProps(['source', 'value'])

const editorFocused = ref(false)

const editorHeight = computed(() => {
    const lines = (code.value.match(/\n/g) || '').length + 1
    return 14 + (lines * 20)
})

const code = ref(props.value)
const editorRef = shallowRef()

const getExistingFields = (text) => {
    const parser = new Parser()
    parser.parse(text, false)
    return parser.getFieldsNames(props.source, false)
}

const getFieldsNameSuggestions = (existingFields, range) => {
    const suggestions = []
    for (const name of Object.keys(props.source.fields)) {
        if (props.source.fields[name].suggest) {
            if (!existingFields.includes(name)) {
                suggestions.push({
                    label: name,
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    range: range,
                    insertText: name + ',',
                    command: {
                        id: 'editor.action.triggerSuggest',
                    }
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
            }
        })
    }
    return suggestions
}

const getSuggestions = (word, range, textFull, textBeforeCursor) => {
    let suggestions = []
    const parser = new Parser()
    parser.parse(textBeforeCursor)
    if (parser.state == State.EXPECT_MODIFIER) {
        suggestions = getModifiersSuggestions(range)
    } else if (parser.state == State.MODIFIER) {
        if (!Object.keys(MODIFIERS).includes(word)) {
            suggestions = getModifiersSuggestions(range)
        }
    }
    else if (parser.state == State.EXPECT_NAME || parser.state == State.NAME) {
        suggestions = getFieldsNameSuggestions(getExistingFields(textFull), range)
    }
    return suggestions
}

const handleMount = editor => {
    monaco.languages.registerCompletionItemProvider('fields', {
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

    editorRef.value = editor
    editor.addAction({
        id: 'submit',
        label: 'submit',
        keybindings: [
            monaco.KeyMod.chord(
                monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
            ),
            monaco.KeyMod.chord(
                monaco.KeyMod.Shift | monaco.KeyCode.Enter,
            )
        ],
        run: (e) => {
            emit('submit')
        },
    })
    editor.addAction({
        id: 'triggerSugggest',
        label: 'triggerSuggest',
        keybindings: [
            monaco.KeyCode.Tab
        ],
        run: (e) => {
            editor.trigger('triggerSuggest', 'editor.action.triggerSuggest', {})
        }
    })
    monaco.editor.addKeybindingRule({
        keybinding: monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyF,
        command: null
    });
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
</script>