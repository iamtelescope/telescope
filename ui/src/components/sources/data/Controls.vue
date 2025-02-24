<template>
  <Toolbar class="toolbar-slim border-none p-0 pb-2">
    <template #start>
      <Button icon="pi pi-search" class="mr-2" severity="primary" label="Search" size="small" @click="handleSearch" />
      <Button icon="pi pi-share-alt" class="mr-2" severity="primary" label="Share URL" size="small"
        @click="handleShareURL" :disabled="loading" />
      <Button icon="pi pi-download" class="mr-2" severity="primary" label="Download" size="small"
        @click="handleDownload" :disabled="loading" />
      <Select v-model="limit" :options="limits" optionLabel="value" placeholder="Limit" :size="'small'" class="mr-2" />
      <DatetimePicker @rangeSelect="onRangeSelect" :from="sourceControlsStore.from" :to="sourceControlsStore.to" />
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
  <Message severity="error" v-if="validation != null && !validation.result">
    <span class="text-2xl">Invalid parameters given</span><br>
    <span v-if="validation.non_fields">{{ validation.non_field }}<br></span>
    <span v-for="name in Object.keys(validation.fields)" :key="name"><span class="font-bold">{{ name }}</span>: {{
      validation.fields[name].join(', ') }}<br></span>
  </Message>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

import { Message, Button, Select, Toolbar } from 'primevue'

import DatetimePicker from '@/components/sources/data/DatetimePicker.vue'
import FieldsEditor from '@/components/sources/data/FieldsEditor.vue'
import QueryEditor from '@/components/sources/data/QueryEditor.vue'
import { getLimits } from '@/utils/limits.js'

import { useSourceControlsStore } from '@/stores/sourceControls'

const props = defineProps(['source', 'loading', 'validation'])
const emit = defineEmits(['searchRequest', 'shareURL', 'download'])

const sourceControlsStore = useSourceControlsStore()

const source = ref(props.source)
const limit = ref(sourceControlsStore.limit)
const limits = ref(getLimits(sourceControlsStore.limit.value))

const onRangeSelect = (params) => {
  sourceControlsStore.setFrom(params.from)
  sourceControlsStore.setTo(params.to)
}

const getSearchParams = () => {
  return {
    searchParams: {
      query: sourceControlsStore.query,
      fields: sourceControlsStore.fields,
      limit: sourceControlsStore.limit.value,
      from: new Date(`${sourceControlsStore.from}`).valueOf() || sourceControlsStore.from,
      to: new Date(`${sourceControlsStore.to}`).valueOf() || sourceControlsStore.to,
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
  emit('searchRequest', getSearchParams())
}

const handleDownload = () => {
  emit('download')
}

const handleShareURL = () => {
  emit('shareURL', getSearchParams())
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