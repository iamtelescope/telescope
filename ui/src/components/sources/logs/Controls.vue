<template>
  <Toolbar class="toolbar-slim border-none p-0 pb-2">
    <template #start>
      <Button icon="pi pi-search" class="mr-2" severity="primary" label="Search" size="small" @click="handleSearch" />
      <Button icon="pi pi-share-alt" class="mr-2" severity="primary" label="Share URL" size="small"
        @click="handleShareURL" :disabled="loading" />
      <Button icon="pi pi-download" class="mr-2" severity="primary" label="Download" size="small"
        @click="handleDownload" :disabled="loading" />
      <Select v-model="limit" :options="limits" optionLabel="value" placeholder="Limit" :size="'small'" class="mr-2" />
      <DatetimePicker @rangeSelect="onRangeSelect" :from="props.from" :to="props.to" />
    </template>
  </Toolbar>
  <div class="mb-2">
    <FieldsEditor @change="onFieldsChange" :source="source"
      :value="route.query.fields ?? source.defaultChosenFields.join(', ')" @submit="handleSearch" />
  </div>
  <div class="mb-3">
    <QueryEditor @change="onQueryChange" :source="source" :value="route.query.query ?? ''" :from="from" :to="to" @submit="handleSearch" />
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
import { useRoute } from 'vue-router'

import { Message, Button, Select, Toolbar } from 'primevue'

import DatetimePicker from '@/components/sources/logs/DatetimePicker.vue'
import FieldsEditor from '@/components/sources/logs/FieldsEditor.vue'
import QueryEditor from '@/components/sources/logs/QueryEditor.vue'
import { getLimits } from '@/utils/limits.js'

const props = defineProps(['source', 'loading', 'from', 'to', 'validation'])
const emit = defineEmits(['searchRequest', 'shareURL', 'download'])

const route = useRoute()

const from = ref(null)
const to = ref(null)
const source = ref(props.source)
const query = ref(route.query.query ?? '')
const fields = ref(route.query.fields ?? source.value.defaultChosenFields.join(', '))
let queryLimit = 50

if (route.query.limit) {
  let intLimit = parseInt(route.query.limit)
  if (!isNaN(intLimit)) {
    queryLimit = intLimit
  }
}

const limit = ref({ "value": queryLimit })
const limits = ref(getLimits(queryLimit))

const onRangeSelect = (params) => {
  from.value = params.from
  to.value = params.to
}

const getSearchParams = () => {
  return {
    searchParams: {
      query: query.value,
      fields: fields.value,
      limit: limit.value.value,
      from: new Date(`${from.value}`).valueOf() || from.value,
      to: new Date(`${to.value}`).valueOf() || to.value,
    },
    source: source.value,
  }
}

const onFieldsChange = (value) => {
  fields.value = value
}

const onQueryChange = (value) => {
  query.value = value
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

watch(props, () => {
  if (props.from && props.to) {
    from.value = props.from
    to.value = props.to
  }
})
</script>