<template>
    <AccessDenied v-if="!hasPermission" message="You don't have permission to create connections." />
    <ConnectionWizard v-else />
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import ConnectionWizard from '@/components/connections/wizard/ConnectionWizard.vue'
import AccessDenied from '@/components/common/AccessDenied.vue'

const { user } = storeToRefs(useAuthStore())

const hasPermission = computed(() => {
    return user.value?.canCreateConnection() || false
})
</script>
