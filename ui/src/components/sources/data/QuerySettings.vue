<template>
    <Button icon="pi pi-search" class="mr-2" label="Query setup" text size="small" @click="toggleSettings" />
    <Popover ref="dropdown" :pt="{ content: { class: 'p-0' } }">
        <div class="flex w-full">
            <div class="flex flex-col">
                <DataRow name="Enable raw query editor" class="pl-3 pr-2">
                    <ToggleSwitch v-model="enableRawQueryEditor" @change="onEnableRawQueryEditorChange"
                        :readonly="!source.isRawQueryAllowed()" v-tooltip="enableRawQueryEditorTooltip" class="mt-2"/>
                </DataRow>
            </div>
        </div>
    </Popover>
</template>

<script setup>
import { ref, computed } from 'vue'

import { Popover, Button, ToggleSwitch } from 'primevue'

import DataRow from '@/components/common/DataRow.vue'

const props = defineProps(["source", "enableRawQueryEditorInitial"])
const emit = defineEmits(['enableRawQueryEditorChange'])


const dropdown = ref()
const enableRawQueryEditor = ref(props.enableRawQueryEditorInitial)

const enableRawQueryEditorTooltip = computed(() => {
    if (!props.source.isRawQueryAllowed()) {
        return { value: 'Insufficient permissions to use source raw queries', showDelay: 300 }
    }
})

const onEnableRawQueryEditorChange = () => {
    emit('enableRawQueryEditorChange', enableRawQueryEditor.value)
}

const toggleSettings = (event) => {
    dropdown.value.toggle(event)
}
</script>