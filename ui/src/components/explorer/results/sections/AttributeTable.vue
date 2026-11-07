<template>
    <table class="w-full text-xs">
        <tr
            v-for="item in rows"
            :key="item.path.join('\u0000')"
            class="group border-t border-neutral-100 dark:border-neutral-800 align-top"
            data-testid="row-attribute"
        >
            <td class="py-1 pr-3 font-mono text-neutral-600 dark:text-neutral-400 break-all w-2/5">
                {{ item.key }}
            </td>
            <td class="py-1 font-mono break-all whitespace-pre-wrap">{{ display(item.value) }}</td>
            <td v-if="filterable" class="py-0.5 pl-2 w-16 text-nowrap text-right">
                <FilterButtons :path="item.path" :value="item.value" :label="item.key" />
            </td>
        </tr>
    </table>
</template>

<script setup>
import FilterButtons from '@/components/explorer/results/sections/FilterButtons.vue'

defineProps({ rows: Array, filterable: { type: Boolean, default: true } })

const display = (value) => {
    if (value === null || value === undefined || value === '') return '–'
    return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
</script>
