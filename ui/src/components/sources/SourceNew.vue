<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <SourceForm />
        </div>
    </div>
</template>

<script setup>
import { useNavStore } from '@/stores/nav'

import SourceForm from '@/components/sources/SourceForm.vue'

const navStore = useNavStore()

navStore.updatev2([
    'sources',
    'New',
])
</script>