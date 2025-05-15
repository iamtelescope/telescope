<template>
  <div>
    <Toolbar class="toolbar-slim border-none p-0 pt-1">
      <template #start>
        <Button
            class="mr-2"
            :class="{'bg-orange-600 border-orange-700 hover:bg-orange-700 dark:hover:text-white': paramsChanged}"
            :label="loading ? 'Cancel' : 'Execute'"
            size="small"
            :disabled="false"
            @click="handleSearch"
        >
          <template #icon>
            <i v-if="loading" class="pi pi-spin pi-spinner"></i>
            <i v-else class="pi pi-caret-right"></i>
          </template>
        </Button>
        <Button
            icon="pi pi-share-alt"
            class="mr-2"
            severity="primary"
            label="Share URL"
            size="small"
            @click="handleShareURL"
            :disabled="loading"
        />
        <Button
            icon="pi pi-download"
            class="mr-2"
            severity="primary"
            label="Download"
            size="small"
            @click="handleDownload"
            :disabled="loading"
        />
        <FloatLabel variant="on">
          <Select
              v-model="limit"
              :options="limits"
              placeholder="Limit"
              size="small"
              class="mr-2"
              @update:model-value="sourceControlsStore.setLimit"
          />
          <label>Limit</label>
        </FloatLabel>
        <DatetimePicker
            @rangeSelect="onRangeSelect"
            :from="sourceControlsStore.from"
            :to="sourceControlsStore.to"
        />
        <QuerySettings
            :source="source"
            :enableRawQueryEditorInitial="showRawQueryEditor"
            @enableRawQueryEditorChange="onEnableRawQueryEditorChange"
        />
        <GraphSettings
            :source="source"
            :groupByInvalid="groupByInvalid"
            :showGraph="sourceControlsStore.showGraph"
            :graphGroupBy="sourceControlsStore.graphGroupBy"
            @graphVisibilityChanged="onGraphVisibilityChanged"
        />
      </template>
      <template #end>
        <SavedViews :savedView="savedView" :source="source" class="mr-2" @change="onSavedViewChanged"/>
        <ToggleButton
            v-model="hideFilters"
            onLabel="Show"
            offLabel="Hide"
            onIcon="pi pi-eye"
            offIcon="pi pi-eye-slash"
            size="small"
            class="mr-2"
        />
      </template>
    </Toolbar>
    <div :class="{ hidden: hideFilters }">
      <div class="mb-2 mt-3">
        <IftaLabel>
          <FieldsEditor
              id="fields_editor"
              @change="onFieldsChange"
              :source="source"
              :value="sourceControlsStore.fields"
              @submit="handleSearch"
          />
          <label for="fields_editor">Fields selector</label>
        </IftaLabel>
      </div>
      <div class="mb-2">
        <ContextFields
            v-if="source.contextFields"
            :source="source"
            :contextFields="sourceControlsStore.contextFields"
            @fieldChanged="onContextFieldChanged"
        />
      </div>
      <div class="mb-2">
        <IftaLabel>
          <QueryEditor
              id="flyql_editor"
              @change="onQueryChange"
              :source="source"
              :value="sourceControlsStore.query"
              :from="sourceControlsStore.from.value"
              :to="sourceControlsStore.to.value"
              @submit="handleSearch"
          />
          <label for="flyql_editor">FlyQL query</label>
        </IftaLabel>
      </div>
      <div v-if="source.isRawQueryAllowed() && showRawQueryEditor">
        <IftaLabel>
          <RawQueryEditor
              id="raw_query_editor"
              @change="onRawQueryChange"
              :source="source"
              :value="sourceControlsStore.rawQuery"
              @submit="handleSearch"
          />
          <label for="raw_query_editor">RAW query (SQL WHERE statement)</label>
        </IftaLabel>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, watch, onMounted} from 'vue'

import {Button, Select, Toolbar, FloatLabel, IftaLabel, ToggleButton} from 'primevue'

import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import GraphSettings from '@/components/explorer/controls/GraphSettings.vue'
import QuerySettings from '@/components/explorer/controls/QuerySettings.vue'
import ContextFields from '@/components/explorer/controls/ContextFields.vue'
import FieldsEditor from '@/components/explorer/controls/FieldsEditor.vue'
import QueryEditor from '@/components/explorer/controls/QueryEditor.vue'
import RawQueryEditor from '@/components/explorer/controls/RawQueryEditor.vue'
import SavedViews from '@/components/explorer/controls/saved_views/SavedViews.vue'
import {getLimits} from '@/utils/limits.js'

import {useSourceControlsStore} from '@/stores/sourceControls'

const props = defineProps(['source', 'loading', 'groupByInvalid', 'savedView', 'paramsChanged'])
const emit = defineEmits(['searchRequest', 'searchCancel', 'shareURL', 'download', 'graphVisibilityChanged'])

const sourceControlsStore = useSourceControlsStore()

const hideFilters = ref(false)

const source = ref(props.source)
const showRawQueryEditor = ref(sourceControlsStore.rawQuery ? true : false)
const storedRawQuery = ref('')
const limit = ref(sourceControlsStore.limit)
const limits = ref(getLimits(sourceControlsStore.limit))

const onRangeSelect = (params) => {
  sourceControlsStore.setFrom(params.from)
  sourceControlsStore.setTo(params.to)
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
    sourceControlsStore.setRawQuery('')
  }
}

const onRawQueryChange = (value) => {
  sourceControlsStore.setRawQuery(value)
}

const onContextFieldChanged = (params) => {
  sourceControlsStore.setContextField(params.name, params.value)
}

const onGraphVisibilityChanged = () => {
  emit('graphVisibilityChanged')
}

const onSavedViewChanged = (view) => {
  sourceControlsStore.setView(view)
}

const handleSearch = () => {
  if (props.loading) {
    emit('searchCancel')
  } else {
    emit('searchRequest')
  }
}

const handleDownload = () => {
  emit('download')
}

const handleShareURL = () => {
  emit('shareURL')
}

onMounted(() => {
  handleSearch()
})

defineExpose({onRangeSelect, handleSearch})

watch(() => sourceControlsStore.limit, (newLimit) => {
  limit.value = newLimit;
})

</script>
