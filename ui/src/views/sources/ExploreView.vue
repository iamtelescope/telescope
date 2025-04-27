<template>
    <div v-if="loading">
        <Loader />
    </div>
    <div v-else>
        <div v-if="error">
            <Error :error="error" />
        </div>
        <div v-else>
            <Explorer :source="source" v-if="source" />
        </div>
    </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

import { useGetSource } from '@/composables/sources/useSourceService'

import Error from '@/components/common/Error.vue'
import Loader from '@/components/common/Loader.vue'
import Explorer from '@/components/explorer/Explorer.vue'

const route = useRoute()
const { source, error, loading } = useGetSource(route.params.sourceSlug)
</script>
