<template>
    <Button
        icon="pi pi-chart-bar"
        class="mr-2"
        :class="{ 'text-red-500': groupByInvalid }"
        label="Graph setup"
        text
        size="small"
        @click="toggleSettings"
    />
    <Popover ref="dropdown" :pt="{ content: { class: 'p-0' } }">
        <div class="flex w-full">
            <div class="flex flex-col">
                <DataRow name="Visible" class="pl-3 pr-2" :showBorder="showGraph">
                    <ToggleSwitch v-model="showGraph" @change="onShowGraphChange" class="mt-2" />
                </DataRow>
                <DataRow v-if="showGraph" name="Group By" :showBorder="false" class="pl-3 pr-2">
                    <Select
                        size="small"
                        v-model="groupBy"
                        :options="groupByOptions"
                        optionLabel="name"
                        editable
                        :showClear="groupBy != ''"
                        @change="onGraphGroupByChange"
                        :invalid="groupByInvalid"
                        :virtualScrollerOptions="{ itemSize: 38 }"
                        :filterFields="['name']"
                    >
                    </Select>
                </DataRow>
            </div>
        </div>
    </Popover>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Popover, Button, ToggleSwitch, Select } from 'primevue'

import { useSourceControlsStore } from '@/stores/sourceControls'
import DataRow from '@/components/common/DataRow.vue'

const route = useRoute()
const props = defineProps(['source', 'groupByInvalid', 'showGraph', 'graphGroupBy'])
const emit = defineEmits(['graphVisibilityChanged'])

const sourceControlsStore = useSourceControlsStore()
const dropdown = ref()
const showGraph = ref(props.showGraph)
const groupBy = ref(props.graphGroupBy ? props.graphGroupBy : null)

const onGraphGroupByChange = (event) => {
    let value = event.value
    if (typeof value == 'object') {
        if (value === null) {
            value = ''
        } else {
            value = value.name
        }
    }
    sourceControlsStore.setGraphGroupBy(value)
}

const onShowGraphChange = () => {
    sourceControlsStore.setShowGraph(showGraph.value)
    emit('graphVisibilityChanged')
}

const groupByOptions = computed(() => {
    let result = []
    for (const [key, value] of Object.entries(props.source.fields)) {
        if (value.group_by) {
            result.push({ name: key })
        }
    }
    return result
})

watch(
    () => sourceControlsStore.graphGroupBy,
    (newGraphGroupBy) => {
        groupBy.value = newGraphGroupBy
    },
)

watch(
    () => sourceControlsStore.showGraph,
    (newShowGraph) => {
        showGraph.value = newShowGraph
        emit('graphVisibilityChanged')
    },
)

const toggleSettings = (event) => {
    dropdown.value.toggle(event)
}
</script>
