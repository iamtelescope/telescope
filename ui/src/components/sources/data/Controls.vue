<template>
    <Toolbar class="toolbar-slim border-none p-0 pb-2">
        <template #start>
            <Button icon="pi pi-search" class="mr-2" severity="primary" label="Search" size="small"
                @click="handleSearch" />
            <Button icon="pi pi-share-alt" class="mr-2" severity="primary" label="Share URL" size="small"
                @click="handleShareURL" :disabled="loading" />
            <Button icon="pi pi-download" class="mr-2" severity="primary" label="Download" size="small"
                @click="handleDownload" :disabled="loading" />
            <FloatLabel variant="on">
                <Select v-model="limit" :options="limits" optionLabel="value" placeholder="Limit" size="small"
                    class="mr-2" />
                <label>Limit</label>
            </FloatLabel>
            <DatetimePicker @rangeSelect="onRangeSelect" :from="sourceControlsStore.from"
                :to="sourceControlsStore.to" />
            <FloatLabel variant="on">
                <Select size="small" v-model="groupBy" :options="groupByOptions" optionLabel="name" editable
                    :showClear="groupBy != ''" class="ml-2" @change="onGraphGroupByChange" :invalid="groupByInvalid">
                </Select>
                <label>Graph group by</label>
            </FloatLabel>
        </template>
    </Toolbar>
    <div class="mb-2">
        <FieldsEditor @change="onFieldsChange" :source="source" :value="sourceControlsStore.fields"
            @submit="handleSearch" />
    </div>
    <div class="mb-3">
        <QueryEditor @change="onQueryChange" :source="source" :value="sourceControlsStore.query"
            :from="sourceControlsStore.from" :to="sourceControlsStore.to" @submit="handleSearch" />
    </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from "vue"

import { Button, Select, Toolbar, FloatLabel } from "primevue"

import DatetimePicker from "@/components/sources/data/DatetimePicker.vue"
import FieldsEditor from "@/components/sources/data/FieldsEditor.vue"
import QueryEditor from "@/components/sources/data/QueryEditor.vue"
import { getLimits } from "@/utils/limits.js"

import { useSourceControlsStore } from "@/stores/sourceControls"

const props = defineProps(["source", "loading","groupByInvalid"])
const emit = defineEmits(["searchRequest", "shareURL", "download"])

const sourceControlsStore = useSourceControlsStore()

const source = ref(props.source)
const limit = ref(sourceControlsStore.limit)
const limits = ref(getLimits(sourceControlsStore.limit.value))
const groupBy = ref(sourceControlsStore.graphGroupBy ? sourceControlsStore.graphGroupBy : null)

const onGraphGroupByChange = (event) => {
    let value = event.value
    if (typeof (value) == 'object') {
        if (value === null) {
            value = ''
        } else {
            value = value.name
        }
    }
    sourceControlsStore.setGraphGroupBy(value)
}

const onRangeSelect = (params) => {
    sourceControlsStore.setFrom(params.from);
    sourceControlsStore.setTo(params.to);
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

const getSearchParams = () => {
    return {
        searchParams: {
            query: sourceControlsStore.query,
            fields: sourceControlsStore.fields,
            limit: sourceControlsStore.limit.value,
            from:
                new Date(`${sourceControlsStore.from}`).valueOf() ||
                sourceControlsStore.from,
            to:
                new Date(`${sourceControlsStore.to}`).valueOf() ||
                sourceControlsStore.to,
            graph_group_by: sourceControlsStore.graphGroupBy || "",
        },
        source: source.value,
    }
}

const onFieldsChange = (value) => {
    sourceControlsStore.setFields(value)
}

const onQueryChange = (value) => {
    sourceControlsStore.setQuery(value)
}

const handleSearch = () => {
    emit("searchRequest", getSearchParams())
}

const handleDownload = () => {
    emit("download");
}

const handleShareURL = () => {
    emit("shareURL", getSearchParams())
}

onMounted(() => {
    handleSearch()
})

defineExpose({ onRangeSelect, handleSearch })

watch(sourceControlsStore, () => {
    limit.value = sourceControlsStore.limit
})

watch(limit, () => {
    sourceControlsStore.setLimit(limit.value)
})
</script>
