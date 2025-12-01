<template>
    <DockerContextFields
        v-if="source.kind == 'docker'"
        :source="source"
        :containers="contextFields.container"
        @fieldChanged="onFieldChanged"
    />
    <KubernetesContextFields
        v-else-if="source.kind == 'kubernetes'"
        :source="source"
        :deployment="contextFields.deployment"
        @fieldChanged="onFieldChanged"
    />
</template>
<script setup>
import DockerContextFields from '@/components/explorer/controls/DockerContextFields.vue'
import KubernetesContextFields from '@/components/explorer/controls/KubernetesContextFields.vue'
const props = defineProps(['source', 'contextFields'])
const emit = defineEmits(['fieldChanged'])

const onFieldChanged = (params) => {
    emit('fieldChanged', params)
}
</script>
