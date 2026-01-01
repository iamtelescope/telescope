<template>
    <DockerContextFields
        v-if="source.kind == 'docker'"
        :source="source"
        :contextFields="contextFields"
        :contextFieldsData="contextFieldsData"
        @fieldChanged="onFieldChanged"
    />
    <KubernetesContextFields
        v-else-if="source.kind == 'kubernetes'"
        :source="source"
        :contextFields="contextFields"
        :contextFieldsData="contextFieldsData"
        @fieldChanged="onFieldChanged"
    />
</template>
<script setup>
import DockerContextFields from '@/components/explorer/controls/DockerContextFields.vue'
import KubernetesContextFields from '@/components/explorer/controls/KubernetesContextFields.vue'

const props = defineProps(['source', 'contextFields', 'contextFieldsData'])
const emit = defineEmits(['fieldChanged'])

const onFieldChanged = (params) => {
    emit('fieldChanged', params)
}
</script>
