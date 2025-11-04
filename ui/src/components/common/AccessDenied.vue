<template>
    <Content>
        <template #header>
            <Header>
                <template #title>
                    <ShieldAlert class="mr-3 w-8 h-8" />
                    Access Denied
                </template>
            </Header>
        </template>
        <template #content>
            <div class="flex flex-col items-center justify-center py-4 max-w-[600px]">
                <Message severity="error" class="w-full">
                    {{ message || "You don't have permission to access this resource." }}
                </Message>
            </div>
        </template>
    </Content>
</template>

<script setup>
import { ShieldAlert } from 'lucide-vue-next'
import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import Message from 'primevue/message'

defineProps({
    message: {
        type: String,
        default: "You don't have permission to access this resource.",
    },
})
</script>
