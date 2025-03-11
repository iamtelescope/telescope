<template>
    <div>
        <Toolbar class="toolbar-slim border-none p-0 pb-2 pt-1">
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
                <QuerySettings :source="source" :enableRawQueryEditorInitial="showRawQueryEditor" @enableRawQueryEditorChange="onEnableRawQueryEditorChange"/>
                <GraphSettings :source="source" :groupByInvalid="groupByInvalid" @graphVisibilityChanged="onGraphVisibilityChanged"/>
            </template>
        </Toolbar>
        <div class="mb-2">
            <IftaLabel>
                <FieldsEditor id="fields_editor" @change="onFieldsChange" :source="source"
                    :value="sourceControlsStore.fields" @submit="handleSearch" />
                <label for="fields_editor">Fields selector</label>
            </IftaLabel>
        </div>
        <div class="mb-2">
            <IftaLabel>
                <QueryEditor id="flyql_editor" @change="onQueryChange" :source="source"
                    :value="sourceControlsStore.query" :from="sourceControlsStore.from" :to="sourceControlsStore.to"
                    @submit="handleSearch" />
                <label for="flyql_editor">FlyQL query</label>
            </IftaLabel>
        </div>
        <div v-if="source.isRawQueryAllowed() && showRawQueryEditor">
            <IftaLabel>
                <RawQueryEditor id="raw_query_editor" @change="onRawQueryChange" :source="source"
                    :value="sourceControlsStore.rawQuery" @submit="handleSearch" />
                <label for="raw_query_editor">RAW query (SQL WHERE statement)</label>
            </IftaLabel>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from "vue"

import { Button, Select, Toolbar, FloatLabel, IftaLabel, ToggleSwitch } from "primevue"

import DatetimePicker from "@/components/sources/data/DatetimePicker.vue"
import GraphSettings from "@/components/sources/data/GraphSettings.vue"
import QuerySettings from "@/components/sources/data/QuerySettings.vue"
import FieldsEditor from "@/components/sources/data/FieldsEditor.vue"
import QueryEditor from "@/components/sources/data/QueryEditor.vue"
import RawQueryEditor from "@/components/sources/data/RawQueryEditor.vue"
import { getLimits } from "@/utils/limits.js"

import { useSourceControlsStore } from "@/stores/sourceControls"

const props = defineProps(["source", "loading", "groupByInvalid"])
const emit = defineEmits(["searchRequest", "shareURL", "download", "graphVisibilityChanged"])

const sourceControlsStore = useSourceControlsStore()

const source = ref(props.source)
const showRawQueryEditor = ref(sourceControlsStore.rawQuery ? true : false)
const storedRawQuery = ref("")
const limit = ref(sourceControlsStore.limit)
const limits = ref(getLimits(sourceControlsStore.limit.value))

const onToggleShowRawQueryEditor = () => {
    if (showRawQueryEditor.value) {
        if (storedRawQuery.value) {
            sourceControlsStore.setRawQuery(storedRawQuery.value)
        }
    } else {
        storedRawQuery.value = sourceControlsStore.rawQuery
        sourceControlsStore.setRawQuery("")
    }
}

const onRangeSelect = (params) => {
    sourceControlsStore.setFrom(params.from);
    sourceControlsStore.setTo(params.to);
}


const onFieldsChange = (value) => {
    sourceControlsStore.setFields(value)
}

const onQueryChange = (value) => {
    sourceControlsStore.setQuery(value)
}

const onEnableRawQueryEditorChange = (value) => {
    showRawQueryEditor.value = value
    if (showRawQueryEditor.value) {
        if (storedRawQuery.value) {
            sourceControlsStore.setRawQuery(storedRawQuery.value)
        }
    } else {
        storedRawQuery.value = sourceControlsStore.rawQuery
        sourceControlsStore.setRawQuery("")
    }
}

const onRawQueryChange = (value) => {
    sourceControlsStore.setRawQuery(value)
}

const onGraphVisibilityChanged = () => {
    emit('graphVisibilityChanged')
}

const handleSearch = () => {
    emit("searchRequest")
}

const handleDownload = () => {
    emit("download");
}

const handleShareURL = () => {
    emit("shareURL")
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
