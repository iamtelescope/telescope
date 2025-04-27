<template>
    <DockerContextFields
        v-if="source.kind == 'docker'"
        :source="source"
        :containers="contextFields.container"
        @fieldChanged="onFieldChanged"
    />
</template>
<script setup>
import DockerContextFields from '@/components/explorer/DockerContextFields.vue'
const props = defineProps(['source', 'contextFields'])
const emit = defineEmits(['fieldChanged'])

const onFieldChanged = (params) => {
    emit('fieldChanged', params)
}
</script>
