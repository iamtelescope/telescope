<template>
    <Controls ref="controlsRef" @searchRequest="onSearchRequest" @shareURL="onShareURL" @download="onDownload"
        :source="source" :loading="loading" :from="from" :to="to" :validation="validation" />
    <div class="flex justify-content-center	w-full">
        <Loader v-if="loading" />
        <div v-else style="padding: 0px; width: 100%;">
            <Error :error="error" v-if="error" />
            <div v-else>
                <Histogramm v-if="metadata" :timestamps="metadata.stats.timestamps" :data="metadata.stats.data"
                    :meta="metadata.stats.meta" :source="source" class="mb-3"
                    @rangeSelected="onHistogrammRangeSelected" />
                <LimitMessage v-if="metadata" :meta="metadata.stats.meta"></LimitMessage>
                <SourceDataTable v-if="rows && source" :source="source" :rows="rows" :metadata="metadata"
                    :timezone="timezone" />
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import { useToast } from 'primevue'

import { useNavStore } from '@/stores/nav'

import { useGetSourceData } from '@/composables/sources/useSourceService'
import Controls from '@/components/sources/data/Controls.vue'
import Loader from '@/components/common/Loader.vue'
import Error from '@/components/common/Error.vue'
import SourceDataTable from '@/components/sources/data/SourceDataTable.vue'
import Histogramm from "@/components/sources/data/Histogramm.vue"
import LimitMessage from '@/components/sources/data/LimitMessage.vue'

const controlsRef = ref(null)

const navStore = useNavStore()
const route = useRoute()
const toast = useToast()

const from = ref()
const to = ref()
const timezone = ref('UTC')

const props = defineProps(['source'])

const { rows, metadata, error, loading, validation, load } = useGetSourceData()

const onSearchRequest = (params) => {
    rows.value = null
    let queryString = new URLSearchParams(params.searchParams).toString();
    let url = route.path + "?" + queryString
    window.history.pushState('', 'telescope', url)
    load(props.source.slug, params.searchParams)
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
    from.value = params.from
    to.value = params.to
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
</script>