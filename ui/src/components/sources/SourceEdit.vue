<template>
    <DataView :loadings="[sourceLoading]" :errors="[sourceError]">
        <template v-if="source && !source.isEditable()">
            <AccessDenied message="You don't have permission to edit this source." />
        </template>
        <template v-else-if="source">
            <SourceEditContent :source="source" />
        </template>
    </DataView>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useGetSource } from '@/composables/sources/useSourceService'
import DataView from '@/components/common/DataView.vue'
import AccessDenied from '@/components/common/AccessDenied.vue'
import SourceEditContent from '@/components/sources/SourceEditContent.vue'

const route = useRoute()

// Load the source first to check permissions
const { source, error: sourceError, loading: sourceLoading } = useGetSource(route.params.sourceSlug)
</script>
