<template>
    <Controls ref="controlsRef" @searchRequest="onSearchRequest" @shareURL="onShareURL" @download="onDownload"
        :source="source" :loading="loading" :validation="validation" />
    <BorderCard class="mb-3" :loading="graphLoading">
        <Skeleton v-if="!graphData && !graphError" width="100%" height="235px"></Skeleton>
        <Error v-if="graphError" :error="graphError"></Error>
        <Histogramm v-if="graphData && !graphError" :stats="graphData" :source="source"
            @rangeSelected="onHistogrammRangeSelected" :rows="rows"/>
    </BorderCard>
    <BorderCard :loading="loading">
        <Skeleton v-if="!rows && !error" width="100%" height="400px"></Skeleton>
        <Error v-if="error" :error="error"></Error>
        <LimitMessage v-if="fields && graphData && !error && !graphError" :rowsCount="rows.length" :totalCount="graphData.total"></LimitMessage>
        <SourceDataTable v-if="rows && !error" :source="source" :rows="rows" :fields="fields"
            :timezone="timezone" />
    </BorderCard>
</template>

<script setup>
import { ref, onBeforeMount, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useToast } from 'primevue'

import { useNavStore } from '@/stores/nav'

import { Skeleton } from 'primevue'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { useGetSourceData, useGetSourceGraphData } from '@/composables/sources/useSourceService'
import Controls from '@/components/sources/data/Controls.vue'
import BorderCard from '@/components/common/BorderCard.vue'
import Error from '@/components/common/Error.vue'
import SourceDataTable from '@/components/sources/data/SourceDataTable.vue'
import Histogramm from "@/components/sources/data/Histogramm.vue"
import LimitMessage from '@/components/sources/data/LimitMessage.vue'

const controlsRef = ref(null)

const navStore = useNavStore()
const route = useRoute()
const toast = useToast()
const sourceControlsStore = useSourceControlsStore()
const timezone = ref('UTC')

const props = defineProps(['source'])

const { rows, fields, error, loading, validation, load } = useGetSourceData()
const {
    data: graphData,
    error: graphError,
    loading: graphLoading,
    validation: graphValidation,
    load: graphLoad
} = useGetSourceGraphData();

const onSearchRequest = (params) => {
    let queryString = new URLSearchParams(params.searchParams).toString();
    let url = route.path + "?" + queryString
    window.history.pushState('', 'telescope', url)
    load(props.source.slug, params.searchParams)
    graphLoad(props.source.slug, params.searchParams)
}

const onShareURL = (params) => {
    let queryString = new URLSearchParams(params.searchParams).toString()
    let url = window.location.origin + route.path + "?" + queryString

    navigator.clipboard.writeText(url)
        .then(() => {
            toast.add({ severity: 'success', summary: 'Success', detail: "URL copied to clipboard", life: 3000 });
        })
        .catch(err => {
            toast.add({ severity: 'error', summary: 'Error', detail: "Failed to copy URL to clipboard", life: 6000 });
        });
}

const onDownload = () => {
    const data = JSON.stringify(rows.value, null, 2)
    const blob = new Blob([data], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "telescope_data.json"
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
    { label: props.source.slug, },
    { label: 'explore' },
])

onBeforeMount(() => {
    sourceControlsStore.init(props.source)
})
watch(() => props.rows, (newValue, oldValue) => {
  console.log(`myProp изменился: ${oldValue} → ${newValue}`);
});
</script>