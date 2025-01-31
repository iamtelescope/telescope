<template>
    <Fieldset class="text-wrap" :class="bgClass">
        <template #legend>
            <ProgressSpinner v-if="loading" style="width: 12px; height: 12px; color:blue" strokeWidth="1"
                fill="transparent" animationDuration="1s" /> <span class="font-bold">Connection test results</span>
        </template>
        <div v-if="loading">
            <div class="flex flex-row">
                <Skeleton width="10rem" class="mb-2 mr-2"></Skeleton>
                <Skeleton width="10rem" class="mb-2"></Skeleton>
            </div>
            <div class="flex flex-row">
                <Skeleton width="10rem" class="mr-2"></Skeleton>
                <Skeleton width="10rem"></Skeleton>
            </div>
        </div>
        <div v-else>
            <div v-if="data">
                <DataRow name="REACHABILITY" :showBorder="false" :noPadding="true" v-if="data.reachability">
                    <span v-if="data.reachability.result" class="text-green-600">
                        <i class="pi pi-check-circle"></i></span>
                    <span v-else class="text-red-600">
                        <pre class="text-wrap"><i class="pi pi-times-circle"></i> {{ data.reachability.error }}</pre>
                    </span>
                </DataRow>
                <hr class="mt-3 mb-3">
                <DataRow name="SCHEMA" :showBorder="false" :noPadding="true" v-if="data.schema">
                    <span v-if="data.schema.result" class="text-green-600">
                        <i class="pi pi-check-circle"></i>
                    </span>
                    <span v-else class="text-orange-400">
                        <pre><i class="pi pi-times-circle"></i> {{ data.schema.error }}...</pre>
                        <pre>...the following steps in the form will not be so convenient without table schema</pre>
                    </span>
                </DataRow>
            </div>
        </div>
    </Fieldset>
</template>

<script setup>
import { computed } from 'vue'
import Fieldset from 'primevue/fieldset'
import ProgressSpinner from 'primevue/progressspinner';

import DataRow from '@/components/common/DataRow.vue'
import Skeleton from 'primevue/skeleton'

const props = defineProps(['data', 'loading', 'show'])

const bgClass = computed(() => {
    if (props.data) {
        if (props.data.reachability?.result && props.data.schema?.result) {
            return 'text-green-600'
        } else {
            return 'text-orange-400'
        }
    } else {
        return ''
    }
})
</script>