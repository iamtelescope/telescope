<template>
    <section class="border-t border-neutral-200 dark:border-neutral-700" :data-testid="testid">
        <button
            type="button"
            class="w-full flex items-center gap-2 px-4 py-2 text-sm font-medium text-left hover:bg-neutral-50 dark:hover:bg-neutral-800"
            :aria-expanded="open"
            @click="open = !open"
        >
            <i class="pi text-xs text-neutral-500" :class="open ? 'pi-chevron-down' : 'pi-chevron-right'"></i>
            <span>{{ title }}</span>
            <span v-if="count !== undefined" class="text-neutral-500 font-normal">({{ count }})</span>
        </button>
        <div v-if="open" class="px-4 pb-3">
            <slot />
        </div>
    </section>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ title: String, count: Number, testid: String, collapsed: Boolean })
const open = ref(!props.collapsed)
</script>
