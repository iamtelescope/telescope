<template>
    <DataView
        :loadings="[sourceLoading, savedViewLoading, contextFieldsLoading]"
        :errors="[sourceError, savedViewError, contextFieldsError]"
    >
        <template #loader>
            <ExplorerLoader />
        </template>
        <Explorer :source="source" :savedView="savedView" :contextFieldsData="contextFieldsData" v-if="source" />
    </DataView>
</template>

<script setup>
import { useRoute } from 'vue-router'

import { useGetSource, useGetSavedView, useGetSourceContextFieldsData } from '@/composables/sources/useSourceService'

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
    data: contextFieldsData,
    error: contextFieldsError,
    loading: contextFieldsLoading,
} = useGetSourceContextFieldsData(route.params.sourceSlug)
</script>
