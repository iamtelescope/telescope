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
                <div v-if="data.data && data.data.result">
                    <div class="text-green-600 dark:text-green-400 mb-3">
                        <i class="pi pi-check-circle mr-1"></i>
                        <span class="font-medium">Connection test passed</span>
                    </div>
                    <div v-if="data.data.matched_contexts && data.data.matched_contexts.length > 0" class="mt-3">
                        <div class="font-medium text-sm mb-2">
                            Matched Contexts ({{ data.data.matched_contexts.length }}):
                        </div>
                        <div class="border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden">
                            <div
                                v-for="(context, index) in data.data.matched_contexts"
                                :key="index"
                                class="p-2 text-sm border-b border-gray-200 dark:border-gray-700 last:border-b-0 font-mono bg-gray-50 dark:bg-gray-800"
                            >
                                <div class="flex flex-col gap-1">
                                    <div>
                                        <span class="text-gray-600 dark:text-gray-400">Name:</span>
                                        <span class="font-semibold">{{ context.name }}</span>
                                    </div>
                                    <div>
                                        <span class="text-gray-600 dark:text-gray-400">Cluster:</span>
                                        {{ context.cluster }}
                                    </div>
                                    <div>
                                        <span class="text-gray-600 dark:text-gray-400">User:</span> {{ context.user }}
                                    </div>
                                    <div>
                                        <span class="text-gray-600 dark:text-gray-400">Namespace:</span>
                                        {{ context.namespace }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
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
