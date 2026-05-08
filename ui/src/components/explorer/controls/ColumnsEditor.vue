<template>
    <FlyqlColumns
        v-model="code"
        :columns="columnsSchema"
        :capabilities="{ transformers: true, renderers: true }"
        :registry="transformerRegistry"
        :renderer-registry="rendererRegistry"
        :dark="isDark"
        :placeholder="placeholder"
        :on-key-discovery="onKeyDiscovery"
        @submit="onSubmit"
        @parse-error="onParseError"
        @diagnostics="onDiagnostics"
    />
</template>

<script setup>
import { ref, computed, watch } from 'vue'

import { useDark } from '@vueuse/core'
import { FlyqlColumns } from 'flyql-vue'

import { transformerRegistry, rendererRegistry } from '@/utils/flyql-registries.js'
import { buildFlyqlColumnSchema } from '@/sdk/flyql.js'
import { SourceService } from '@/sdk/services/source.js'

const sourceSrv = new SourceService()

const emit = defineEmits(['change', 'submit', 'parse-error', 'diagnostics'])
const props = defineProps(['source', 'value', 'from', 'to'])

const isDark = useDark()
const code = ref(props.value)
const columnsSchema = computed(() => buildFlyqlColumnSchema(props.source))
const placeholder = computed(() => props.source.generateColumnsExample())

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

watch(
    () => props.value,
    (value) => {
        code.value = value
    },
)

watch(code, (value) => {
    emit('change', value)
})

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
