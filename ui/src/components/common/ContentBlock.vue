<template>
    <div class="w-full">
        <div class="border rounded-lg dark:border-neutral-600">
            <div class="border-b dark:border-neutral-600" :class="{ 'border-b-0': isCollapsed }">
                <slot name="header" v-if="$slots.header"></slot>
                <div
                    v-else-if="header || $slots.header_text"
                    class="p-2 pl-4 text-lg bg-slate-100 rounded-t-lg dark:bg-slate-800"
                >
                    <div class="flex items-center justify-between">
                        <div class="flex items-center" :class="headerClass">
                            <i
                                v-if="collapsible !== false"
                                :class="isCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-down'"
                                class="text-sm text-gray-500 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 mr-3"
                                @click="toggleCollapse"
                            ></i>
                            <slot name="header_text">{{ header }}</slot>
                        </div>
                        <div class="flex items-center pr-2">
                            <slot name="actions"></slot>
                        </div>
                    </div>
                </div>
            </div>
            <div v-if="!isCollapsed">
                <slot></slot>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps(['header', 'collapsible', 'collapsed', 'headerClass'])

const isCollapsed = ref(props.collapsed || false)

const toggleCollapse = () => {
    if (props.collapsible !== false) {
        isCollapsed.value = !isCollapsed.value
    }
}

// Watch for external collapsed prop changes
watch(
    () => props.collapsed,
    (newVal) => {
        if (newVal !== undefined) {
            isCollapsed.value = newVal
        }
    },
)
</script>
