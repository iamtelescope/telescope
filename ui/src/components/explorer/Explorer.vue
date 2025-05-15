<template>
  <Controls
      ref="controlsRef"
      @searchRequest="onSearchRequest"
      @searchCancel="onSearchCancel"
      @shareURL="onShareURL"
      @download="onDownload"
      :savedView="savedView"
      :source="source"
      :loading="loading"
      :paramsChanged="paramsChanged"
      @graphVisibilityChanged="onGraphVisibilityChanged"
      :groupByInvalid="!!(graphValidation && !graphValidation.result && graphValidation.fields.group_by)"
  />
  <div class="mt-3">
    <BorderCard class="mb-2" :loading="graphLoading" v-if="sourceControlsStore.showGraph">
      <Skeleton v-if="graphLoading && graphData === null" width="100%" height="235px"></Skeleton>
      <Error v-if="graphError" :error="graphError"></Error>
      <ValidationError
          v-if="graphValidation && !graphValidation.result"
          :validation="graphValidation"
          message="Failed to load graph: invalid parameters given"
      />
      <Histogramm
          v-else-if="showHistogramm && graphValidation.result"
          :stats="graphData"
          :source="source"
          @rangeSelected="onHistogrammRangeSelected"
          :rows="rows"
          :groupByLabel="sourceControlsStore.graphGroupBy"
      />
    </BorderCard>
    <BorderCard :loading="loading">
      <Skeleton v-if="loading && rows === null" width="100%" height="400px"></Skeleton>
      <Error v-if="error" :error="error"></Error>
      <ValidationError
          v-if="validation && !validation.result"
          :validation="validation"
          message="Failed to load logs data: invalid parameters given"
      />
      <LimitMessage
          v-if="rows && graphData && !error && !graphError"
          :rowsCount="rows.length"
          :totalCount="graphData.total"
      ></LimitMessage>
      <ExplorerTable
          v-if="showSourceDataTable"
          :source="source"
          :rows="rows"
          :fields="fields"
          :timezone="timezone"
      />
    </BorderCard>
  </div>
</template>

<script setup>
import {ref, onBeforeMount, computed} from 'vue'
import {useRoute, useRouter} from 'vue-router'

import {useToast} from 'primevue'

import {useNavStore} from '@/stores/nav'

import {Skeleton} from 'primevue'
import {useSourceControlsStore} from '@/stores/sourceControls'
import {useGetSourceData, useGetSourceGraphData} from '@/composables/sources/useSourceService'

import Controls from '@/components/explorer/controls/Controls.vue'
import BorderCard from '@/components/common/BorderCard.vue'
import Error from '@/components/common/Error.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import ExplorerTable from '@/components/explorer/results/ExplorerTable.vue'
import Histogramm from '@/components/explorer/results/Histogramm.vue'
import LimitMessage from '@/components/explorer/controls/LimitMessage.vue'

const controlsRef = ref(null)

const navStore = useNavStore()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const sourceControlsStore = useSourceControlsStore()
const timezone = ref('UTC')

const lastSearchRouteQuery = ref(null)
const props = defineProps(['source', 'savedView'])
const {rows, fields, error, loading, validation, load, controller} = useGetSourceData()
const {
  data: graphData,
  error: graphError,
  loading: graphLoading,
  validation: graphValidation,
  load: graphLoad,
  controller: graphController,
} = useGetSourceGraphData()

const paramsChanged = computed(() => {
  return lastSearchRouteQuery.value && (JSON.stringify(lastSearchRouteQuery.value) !== JSON.stringify(sourceControlsStore.routeQuery));
})

const onSearchRequest = () => {
  lastSearchRouteQuery.value = sourceControlsStore.routeQuery
  router.push({path: route.path, query: sourceControlsStore.routeQuery})
  load(props.source.slug, sourceControlsStore.dataRequestParams)
  if (sourceControlsStore.showGraph) {
    graphLoad(props.source.slug, sourceControlsStore.graphRequestParams)
  }
}

const onSearchCancel = () => {
  controller.value.abort()
  graphController.value.abort()
}

const onGraphVisibilityChanged = () => {
  if (sourceControlsStore.showGraph) {
    graphLoad(props.source.slug, sourceControlsStore.graphRequestParams)
  } else {
    graphData.value = null
  }
}

const showHistogramm = computed(() => {
  return graphData.value !== null && !graphError.value && graphValidation.value && graphValidation.value.result
})

const showSourceDataTable = computed(() => {
  return rows.value !== null && !error.value && validation.value && validation.value.result
})

const onShareURL = () => {
  let url = window.location.origin + route.path + '?' + sourceControlsStore.queryString

  navigator.clipboard
      .writeText(url)
      .then(() => {
        toast.add({severity: 'success', summary: 'Success', detail: 'URL copied to clipboard', life: 3000})
      })
      .catch((err) => {
        toast.add({severity: 'error', summary: 'Error', detail: 'Failed to copy URL to clipboard', life: 6000})
      })
}

const onDownload = () => {
  const data = JSON.stringify(rows.value, null, 2)
  const blob = new Blob([data], {type: 'application/json'})
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'telescope_data.json'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const onHistogrammRangeSelected = (params) => {
  sourceControlsStore.setFrom(params.from)
  sourceControlsStore.setTo(params.to)
  controlsRef.value.handleSearch()
}

navStore.update([
  {
    icon: 'pi pi-database',
    label: 'Sources',
    url: '/',
  },
  {label: props.source.slug},
  {label: 'explore'},
])

onBeforeMount(() => {
  sourceControlsStore.$reset()
  sourceControlsStore.init(props.source, props.savedView)
})
</script>
