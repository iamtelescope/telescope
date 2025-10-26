<template>
    <DataView :loadings="[loading]" :errors="[error]">
        <AccessDenied
            v-if="connection && !connection.canEdit()"
            message="You don't have permission to edit this connection."
        />
        <ConnectionWizard v-else :connection="connection" />
    </DataView>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useGetConnection } from '@/composables/connections/useConnectionService'

import DataView from '@/components/common/DataView.vue'
import ConnectionWizard from '@/components/connections/wizard/ConnectionWizard.vue'
import AccessDenied from '@/components/common/AccessDenied.vue'

const route = useRoute()

const connectionId = route.params.connectionId

const { connection, error, loading } = useGetConnection(connectionId)
</script>
