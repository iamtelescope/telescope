<template>
    <Controls ref="controlsRef" @searchRequest="onSearchRequest" :source="source" :loading="loading" :from="from"
        :to="to" :validation="validation"/>
    <div class="flex justify-content-center	w-full">
        <Loader v-if="loading" />
        <div v-else style="padding: 0px; width: 100%;">
            <Error :error="error" v-if="error" />
            <div v-else>
                <Histogramm v-if="metadata" :timestamps="metadata.stats.timestamps" :data="metadata.stats.data"
                    :meta="metadata.stats.meta" :source="source" class="mb-3"
                    @rangeSelected="onHistogrammRangeSelected" />
                <LimitMessage v-if="metadata" :meta="metadata.stats.meta"></LimitMessage>
                <LogsTable v-if="rows && source" :source="source" :rows="rows" :metadata="metadata"
                    :timezone="timezone" />
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import { useNavStore } from '@/stores/nav'

import { useGetLogs } from '@/composables/sources/logs/useLogsService'
import Controls from '@/components/sources/logs/Controls.vue'
import Loader from '@/components/common/Loader.vue'
import Error from '@/components/common/Error.vue'
import LogsTable from '@/components/sources/logs/LogsTable.vue'
import Histogramm from "@/components/sources/logs/Histogramm.vue"
import LimitMessage from '@/components/sources/logs/LimitMessage.vue'

const controlsRef = ref(null)

const navStore = useNavStore()
const route = useRoute()

const from = ref()
const to = ref()
const timezone = ref('UTC')

const props = defineProps(['source'])

const { rows, metadata, error, loading, validation, load } = useGetLogs()

const onSearchRequest = (params) => {
    rows.value = null
    let queryString = new URLSearchParams(params.searchParams).toString();
    let url = route.path + "?" + queryString
    window.history.pushState('', 'telescope', url)
    load(props.source.slug, params.searchParams)
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
