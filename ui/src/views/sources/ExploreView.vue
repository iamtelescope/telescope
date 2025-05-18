<template>
    <DataView :loadings="[sourceLoading, savedViewLoading]" :errors="[sourceError, savedViewError]">
        <Explorer :source="source" :savedView="savedView" v-if="source" />
    </DataView>
</template>

<script setup>
import { useRoute } from 'vue-router'

import { useGetSource, useGetSavedView } from '@/composables/sources/useSourceService'

import DataView from '@/components/common/DataView.vue'
import Explorer from '@/components/explorer/Explorer.vue'

const route = useRoute()
const { source, error: sourceError, loading: sourceLoading } = useGetSource(route.params.sourceSlug)
const {
    savedView: savedView,
    error: savedViewError,
    loading: savedViewLoading,
} = useGetSavedView(route.params.sourceSlug, route.query.view)
</script>
