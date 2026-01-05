<template>
    <DockerContextColumns
        v-if="source.kind == 'docker'"
        :source="source"
        :contextColumns="contextColumns"
        :contextColumnsData="contextColumnsData"
        @columnChanged="onColumnChanged"
    />
    <KubernetesContextColumns
        v-else-if="source.kind == 'kubernetes'"
        :source="source"
        :contextColumns="contextColumns"
        :contextColumnsData="contextColumnsData"
        @columnChanged="onColumnChanged"
    />
</template>
<script setup>
import DockerContextColumns from '@/components/explorer/controls/DockerContextColumns.vue'
import KubernetesContextColumns from '@/components/explorer/controls/KubernetesContextColumns.vue'

const props = defineProps(['source', 'contextColumns', 'contextColumnsData'])
const emit = defineEmits(['columnChanged'])

const onColumnChanged = (params) => {
    emit('columnChanged', params)
}
</script>
