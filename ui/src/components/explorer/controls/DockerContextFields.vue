<template>
    <FloatLabel variant="on">
        <MultiSelect
            id="container"
            v-model="selectedContainers"
            optionLabel="name"
            display="chip"
            :options="containerOptions"
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
                        <div class="pl-2 font-medium">{{ slotProps.option.name }}</div>
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
import { ref, computed, watch } from 'vue'
import { MultiSelect, FloatLabel } from 'primevue'

const props = defineProps(['source', 'contextFields', 'contextFieldsData'])
const emit = defineEmits(['fieldChanged'])

// Helper to ensure array
const ensureArray = (val) => {
    if (!val) return []
    if (Array.isArray(val)) return val
    if (typeof val === 'string') return val.split(',').filter((v) => v)
    return []
}

// Computed: container options from prop data
const containerOptions = computed(() => {
    return props.contextFieldsData?.containers || []
})

// Selected containers as full objects (for MultiSelect display)
const selectedContainers = ref([])

// Initialize selected containers from contextFields
const initSelectedContainers = () => {
    const containerNames = ensureArray(props.contextFields?.container)
    if (containerNames.length > 0 && containerOptions.value.length > 0) {
        selectedContainers.value = containerOptions.value.filter((c) => containerNames.includes(c.name))
    } else {
        selectedContainers.value = []
    }
}

// Initialize on mount when data is available
watch(
    [() => props.contextFields, containerOptions],
    () => {
        initSelectedContainers()
    },
    { immediate: true, deep: true },
)

const onContainersChange = () => {
    const names = selectedContainers.value.map((container) => container.name)
    emit('fieldChanged', {
        name: 'container',
        value: names,
    })
}
</script>
