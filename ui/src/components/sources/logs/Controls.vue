<template>
  <Toolbar class="toolbar-slim">
    <template #start>
      <Button icon="pi pi-search" class="mr-2" severity="primary" label="Search" size="small" @click="handleSearch"
        :loading="loading" />
      <Button icon="pi pi-share-alt" class="mr-2" severity="primary" label="Share URL" size="small" disabled />
      <Button icon="pi pi-download" class="mr-2" severity="primary" label="Download" size="small" disabled />
      <Select v-model="limit" :options="limits" optionLabel="value" placeholder="Limit" :size="'small'" class="mr-2" />
      <DatetimePicker @rangeSelect="onRangeSelect" :from="props.from" :to="props.to" />
    </template>
  </Toolbar>
  <div class="mb-2">
    <InputText v-model="fields" fluid :invalid="validation != null && !validation.result && validation.fields.fields" @keyup.enter="handleSearch"></InputText>
    <ErrorText v-if="validation != null && !validation.result && validation.fields.fields"
      :text="validation.fields.fields">
    </ErrorText>
  </div>
  <div class="mb-3">
    <InputText v-model="query" fluid :invalid="validation != null && !validation.result && validation.fields.query" @keyup.enter="handleSearch"></InputText>
    <ErrorText v-if="validation != null && !validation.result && validation.fields.query"
      :text="validation.fields.query">
    </ErrorText>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import Button from 'primevue/button'
import Select from 'primevue/select'
import Toolbar from 'primevue/toolbar'
import InputText from 'primevue/inputtext'

import DatetimePicker from '@/components/sources/logs/DatetimePicker.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import { getLimits } from '@/utils/limits.js'

const props = defineProps(['source', 'loading', 'from', 'to', 'validation'])
const emit = defineEmits(['searchRequest'])

const route = useRoute()

const from = ref(null)
const to = ref(null)
const source = ref(props.source)
const loading = ref(props.loading)
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

const queryValid = computed(() => {
  if (props.validation != null) {
    if ('query' in props.validation.fields) {
      return false
    }
  }
  return true
})

const onRangeSelect = (params) => {
  from.value = params.from
  to.value = params.to
}

const handleSearch = () => {
  emit('searchRequest', {
    searchParams: {
      query: query.value,
      fields: fields.value,
      limit: limit.value.value,
      from: new Date(`${from.value}`).valueOf() || from.value,
      to: new Date(`${to.value}`).valueOf() || to.value,
    },
    source: source.value,
  })
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

<style scoped>
.toolbar-slim {
  border: none;
  padding: 0px;
  padding-bottom: 10px;
}

input {
  font-family: monospace;
}

.form-control:focus {
  box-shadow: none;
}

select:focus {
  box-shadow: none;
}

.limit-selector {
  max-width: 150px;
  margin-right: 5px;
}

.limit-label {
  font-size: 13px;
  vertical-align: middle;
  padding-top: 6px;
  margin-bottom: 0px;
  padding-right: 5px;
}
</style>
