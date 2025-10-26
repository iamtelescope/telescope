<template>
    <ContentBlock header="Connection test result" :collapsible="false">
        <template #actions>
            <ProgressSpinner
                v-if="loading"
                style="width: 16px; height: 16px"
                strokeWidth="2"
                fill="transparent"
                animationDuration="1s"
            />
        </template>
        <div class="p-4">
            <div v-if="loading">
                <div class="flex flex-row">
                    <Skeleton width="10rem" class="mb-2 mr-2"></Skeleton>
                    <Skeleton width="10rem" class="mb-2"></Skeleton>
                </div>
            </div>
            <div v-else>
                <div v-if="data.data && data.data.result" class="text-green-600 dark:text-green-400">
                    <i class="pi pi-check-circle mr-1"></i>
                    <span class="font-medium">Connection test passed</span>
                </div>
                <div v-else>
                    <div class="text-red-600 dark:text-red-400">
                        <i class="pi pi-times-circle mr-1"></i>
                        <span class="font-medium">Connection test failed</span>
                    </div>
                    <InlineError v-if="data.data?.error" :modelValue="data.data.error" />
                </div>
            </div>
        </div>
    </ContentBlock>
</template>

<script setup>
import ProgressSpinner from 'primevue/progressspinner'
import Skeleton from 'primevue/skeleton'
import ContentBlock from '@/components/common/ContentBlock.vue'
import InlineError from '@/components/common/InlineError.vue'

const props = defineProps(['data', 'loading'])
</script>
