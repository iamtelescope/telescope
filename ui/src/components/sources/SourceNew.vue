<template>
    <AccessDenied v-if="!hasPermission" message="You don't have permission to create sources." />
    <SourceNewContent v-else />
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import AccessDenied from '@/components/common/AccessDenied.vue'
import SourceNewContent from '@/components/sources/SourceNewContent.vue'

const { user } = storeToRefs(useAuthStore())

const hasPermission = computed(() => {
    return user.value?.canCreateSource() || false
})
</script>
