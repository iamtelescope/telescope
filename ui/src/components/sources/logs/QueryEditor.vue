<template>
    <div :style="{ height: `${editorHeight}px` }" class="editor border rounded pl-2 pr-2 mb-2 dark:border-neutral-600"
        :class="{ 'border-sky-800 dark:border-sky-700': editorFocused }">
        <vue-monaco-editor v-model:value="code" :theme="theme" language="flyql" :options="getDefaultMonacoOptions()"
            @mount="handleMount" @change="onChange" />
    </div>
</template>

<script setup>
import { ref, computed, shallowRef, nextTick } from 'vue'

import * as monaco from "monaco-editor"

import { useDark } from '@vueuse/core'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

import { getDefaultMonacoOptions } from '@/utils/monaco.js'

const emit = defineEmits(['change', 'submit'])
const props = defineProps(['value'])

const isDark = useDark()

const editorFocused = ref(false)

const editorHeight = computed(() => {
    const lines = (code.value.match(/\n/g) || '').length + 1
    return 14 + (lines * 20)
})

const theme = computed(() => {
    if (isDark.value) {
        return 'telescope-dark'
    } else {
        return 'telescope'
    }
})

const code = ref(props.value)
const editorRef = shallowRef()
const handleMount = editor => {
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
        run: function (e) {
            emit('submit')
        }
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
    })
    editor.onDidFocusEditorWidget(() => {
        editorFocused.value = true
    })
    editor.onDidBlurEditorWidget(() => {
        editorFocused.value = false
    })
    nextTick(() => {
        editor.focus()
    })
}

const onChange = () => {
    emit('change', code.value)
}
</script>