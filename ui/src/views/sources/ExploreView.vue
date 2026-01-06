<template>
    <DataView
        :loadings="[sourceLoading, savedViewLoading, contextColumnsLoading]"
        :errors="[sourceError, savedViewError, contextColumnsError]"
    >
        <template #loader>
            <ExplorerLoader />
        </template>
        <Explorer :source="source" :savedView="savedView" :contextColumnsData="contextColumnsData" v-if="source" />
    </DataView>
</template>

<script setup>
import { useRoute } from 'vue-router'

import { useGetSource, useGetSavedView, useGetSourceContextColumnsData } from '@/composables/sources/useSourceService'

import DataView from '@/components/common/DataView.vue'
import Explorer from '@/components/explorer/Explorer.vue'
import ExplorerLoader from '@/components/explorer/ExplorerLoader.vue'

const route = useRoute()
const { source, error: sourceError, loading: sourceLoading } = useGetSource(route.params.sourceSlug)
const {
    savedView: savedView,
    error: savedViewError,
    loading: savedViewLoading,
} = useGetSavedView(route.params.sourceSlug, route.query.view)
const {
    data: contextColumnsData,
    error: contextColumnsError,
    loading: contextColumnsLoading,
} = useGetSourceContextColumnsData(route.params.sourceSlug)
</script>
