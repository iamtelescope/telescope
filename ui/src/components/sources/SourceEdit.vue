<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <DataView :loading="loading" :error="error" v-if="source.isEditable()">
                <SourceForm :source="source" :startConnectionTest="true"/>
            </DataView>
        </div>
    </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

import { useNavStore } from '@/stores/nav'
import { useGetSource } from '@/composables/sources/useSourceService'

import DataView from '@/components/common/DataView.vue'
import SourceForm from '@/components/sources/SourceForm.vue'

const route = useRoute()
const navStore = useNavStore()

navStore.updatev2([
    'sources',
    { label: route.params.sourceSlug, 'url': `/sources/${route.params.sourceSlug}` },
    'edit',
])

const { source, error, loading } = useGetSource(route.params.sourceSlug)
</script>