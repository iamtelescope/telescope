<template>
    <FloatLabel variant="on">
        <MultiSelect
            id="container"
            v-model="selectedContainers"
            :initialValues="initialValues"
            optionLabel="name"
            display="chip"
            :options="data"
            :loading="loading"
            class="mr-2 min-w-80"
            :maxSelectedLabels="5"
            filter
            autoFilterFocus
            @change="onContainersChange"
        >
            <template #option="slotProps">
                <div class="flex flex-col">
                    <div class="flex flex-fow items-center">
                        <i
                            class="pi pi-circle-fill text-gray-300"
                            :class="{
                                'text-green-500': slotProps.option.status == 'running',
                                'text-red-500': slotProps.option.status == 'dead',
                            }"
                        ></i>
                        <div class="pl-2">[{{ slotProps.option.status }}]</div>
                        <div class="pl-2 font-bold">{{ slotProps.option.name }}</div>
                    </div>
                </div>
            </template>
            <template #dropdownicon>
                <i class="pi pi-box" />
            </template>
        </MultiSelect>
        <label for="container">Container</label>
    </FloatLabel>
</template>
<script setup>
import { ref, onMounted, watch } from 'vue'
import { MultiSelect, FloatLabel } from 'primevue'

import { useGetSourceContextFieldData } from '@/composables/sources/useSourceService'

const props = defineProps(['source', 'containers'])
const emit = defineEmits(['fieldChanged'])

const { data, error, loading, validation, load } = useGetSourceContextFieldData()

const initialValues = ref([])
const selectedContainers = ref([])

const onContainersChange = () => {
    const names = selectedContainers.value.map((container) => container.name)
    emit('fieldChanged', {
        name: 'container',
        value: names,
    })
}

onMounted(() => {
    load(props.source.slug, { field: 'container' })
})

watch(data, () => {
    if (props.containers) {
        for (const container of data.value) {
            if (props.containers.includes(container.name)) {
                selectedContainers.value.push(container)
            }
        }
    }
})
</script>
