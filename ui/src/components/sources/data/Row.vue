<template>
    <div class="flex flex-col h-full w-full overflow-y-auto border-t-4"
        :style="{ borderColor: getColor(row.data[source.severityField]) }">
        <div class="flex flex-col">
            <div class="p-4">
                <Tag value="Primary" :style="{ backgroundColor: getColor(row.data[source.severityField]), color: getContrastColor(getColor(row.data[source.severityField])) }" class="text-gray-900 mr-2 text-bold">{{
                    row.data[source.severityField] }}</Tag>
                <span class="font-mono">{{ row.time.datetime }}.{{ row.time.microseconds }}</span>
            </div>
            <Tabs value="0">
                <TabList>
                    <Tab value="0">FLATTENED</Tab>
                    <Tab value="1">JSON</Tab>
                </TabList>
                <TabPanels :pt="{ root: { className: 'p-0' } }">
                    <TabPanel value="0">
                        <DataTable :value="flattenRow" :row-hover="true" removableSort>
                            <Column field="path" header="PATH" sortable class="font-bold">
                                <template #body="slotProps">
                                    <Button size="small" class="mr-2" :label="FlyQLOperator.EQUALS" severity="secondary"
                                        @click="updateQuery(FlyQLOperator.EQUALS, slotProps.data.path.join(':'), slotProps.data.value)"></Button>
                                    <Button size="small" class="mr-2" :label="FlyQLOperator.NOT_EQUALS"
                                        severity="secondary"
                                        @click="updateQuery(FlyQLOperator.NOT_EQUALS, slotProps.data.path.join(':'), slotProps.data.value)"></Button>
                                    <span class="pr-2 cursor-pointer text-xl"
                                        :class="{ 'text-blue-400': selectedFields.includes(slotProps.data.path.join(':')) }"></span>
                                    <span class="font-mono">{{ slotProps.data.path.join(':') }}</span>
                                </template>
                            </Column>
                            <Column field="value" header="VALUE" sortable>
                                <template #body="slotProps">
                                    <span v-if="slotProps.data.value">
                                        <pre
                                            style="white-space: pre-wrap; word-wrap: break-all; word-break: break-all">{{ slotProps.data.value }}</pre>
                                    </span><span v-else>&ndash;</span>
                                </template>
                            </Column>
                        </DataTable>
                    </TabPanel>
                    <TabPanel value="1">
                        <div class="p-4">
                            <pre
                                style="white-space: pre-wrap; word-wrap: break-all; word-break: break-all">{{ row }}</pre>
                        </div>
                    </TabPanel>
                </TabPanels>
            </Tabs>
        </div>
    </div>
</template>
<script setup>
import { computed } from 'vue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { Operator as FlyQLOperator } from '@/utils/flyql.js'


import { getColor, getContrastColor } from '@/utils/colors.js'
import Tag from 'primevue/tag'

const sourceControlsStore = useSourceControlsStore()

const props = defineProps(['source', 'row'])

const selectedFields = computed(() => {
    return sourceControlsStore.parsedFields(props.source)
})

const updateQuery = (operator, field, value) => {
    sourceControlsStore.addQueryExpression(field, operator, value)
}

function flat_json(result, value, path) {
    if (typeof value === 'object') {
        if (value) {
            for (const [k, v] of Object.entries(value)) {
                let p = [...path]
                p.push(k)
                flat_json(result, v, p)
            }
        } else {
            if (value === null) {
                result.push({ path: path, value: value })
            }
        }
    } else {
        result.push({ path: path, value: value })
    }
    return result
}

const flattenRow = computed(() => {
    return flat_json([], props.row.data, [])
})

</script>