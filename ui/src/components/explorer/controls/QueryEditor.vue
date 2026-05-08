<template>
    <FlyqlEditor
        v-model="code"
        :columns="columnsSchema"
        :registry="transformerRegistry"
        :dark="isDark"
        :placeholder="placeholder"
        :on-autocomplete="onAutocomplete"
        :on-key-discovery="onKeyDiscovery"
        @submit="onSubmit"
        @parse-error="onParseError"
        @diagnostics="onDiagnostics"
    />
</template>

<script setup>
import { ref, computed, watch } from 'vue'

import { useDark } from '@vueuse/core'
import { FlyqlEditor } from 'flyql-vue'

import { transformerRegistry } from '@/utils/flyql-registries.js'
import { buildFlyqlColumnSchema } from '@/sdk/flyql.js'
import { SourceService } from '@/sdk/services/source.js'

const sourceSrv = new SourceService()

const emit = defineEmits(['change', 'submit', 'parse-error', 'diagnostics'])
const props = defineProps(['source', 'value', 'from', 'to'])

const isDark = useDark()
const code = ref(props.value)
const columnsSchema = computed(() => buildFlyqlColumnSchema(props.source))
const placeholder = computed(() => props.source.generateFlyQLExample())

watch(
    () => props.value,
    (value) => {
        code.value = value
    },
)

watch(code, (value) => {
    emit('change', value)
})

async function onAutocomplete(column, value) {
    try {
        const resp = await sourceSrv.autocomplete(props.source.slug, {
            column,
            value,
            from: props.from,
            to: props.to,
        })
        return {
            items: resp.data.items,
            incomplete: resp.data.incomplete,
        }
    } catch (_err) {
        return { items: [], incomplete: false }
    }
}

async function onKeyDiscovery(column, segments) {
    try {
        const resp = await sourceSrv.discoverJsonKeys(props.source.slug, {
            column,
            segments,
            from: props.from,
            to: props.to,
        })
        return resp.data.keys || []
    } catch (_err) {
        return []
    }
}

function onSubmit() {
    emit('submit')
}

function onParseError(err) {
    emit('parse-error', err)
}

function onDiagnostics(diagnostics) {
    emit('diagnostics', diagnostics)
}
</script>
