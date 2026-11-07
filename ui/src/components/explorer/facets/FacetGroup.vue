<template>
    <div class="py-1" :data-testid="`facet-group-${id}`">
        <div class="flex items-center gap-1 group/header">
            <button
                class="flex-1 min-w-0 flex items-center gap-1 text-left text-sm font-semibold truncate py-1 hover:text-primary"
                :title="id"
                @click="open = !open"
                :data-testid="`facet-header-${id}`"
            >
                <i :class="open ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" class="text-xs opacity-60"></i>
                <span class="truncate">{{ title }}</span>
                <span v-if="kind === 'keys'" class="text-xs font-normal opacity-60">keys</span>
            </button>
            <button
                class="px-1 opacity-40 hover:opacity-100"
                :class="{ 'opacity-100 text-primary': pinned }"
                :title="pinned ? 'Unpin' : 'Pin'"
                @click="emit('togglePin')"
                :data-testid="`facet-pin-${id}`"
            >
                <i :class="pinned ? 'pi pi-bookmark-fill' : 'pi pi-bookmark'" class="text-xs"></i>
            </button>
            <button
                v-if="removable"
                class="px-1 opacity-40 hover:opacity-100"
                title="Remove"
                @click="emit('remove')"
                :data-testid="`facet-remove-${id}`"
            >
                <i class="pi pi-times text-xs"></i>
            </button>
        </div>
        <div v-if="open">
            <div v-if="!values.length" class="text-xs opacity-60 pl-4 py-1">No values</div>
            <div
                v-for="(item, i) in shown"
                :key="i"
                class="relative flex items-center gap-1 pl-4 pr-1 text-sm rounded cursor-pointer group/value hover:bg-neutral-100 dark:hover:bg-neutral-800"
                :class="{ 'bg-neutral-100 dark:bg-neutral-800': kind === 'keys' && expandedKeys.includes(item.value) }"
                :title="kind === 'keys' ? 'Show values of this key' : 'Click to filter, Alt+click to exclude'"
                @click="onClick($event, item)"
                :data-testid="`facet-value-${id}-${i}`"
            >
                <div
                    class="absolute left-4 top-0.5 bottom-0.5 rounded-sm bg-neutral-200/70 dark:bg-neutral-700/60"
                    :style="{ width: `calc((100% - 1rem) * ${share(item)})` }"
                ></div>
                <span
                    class="relative flex-1 min-w-0 truncate py-0.5"
                    :class="{ 'italic opacity-60': item.value === null || item.value === '' }"
                    data-testid="facet-value-label"
                    >{{ formatValue(item.value) }}</span
                >
                <template v-if="kind !== 'keys'">
                    <button
                        class="relative hidden group-hover/value:inline px-1 opacity-60 hover:opacity-100"
                        title="Filter for this value"
                        @click.stop="emit('include', item)"
                        :data-testid="`facet-include-${id}-${i}`"
                    >
                        =
                    </button>
                    <button
                        class="relative hidden group-hover/value:inline px-1 opacity-60 hover:opacity-100"
                        title="Exclude this value"
                        @click.stop="emit('exclude', item)"
                        :data-testid="`facet-exclude-${id}-${i}`"
                    >
                        &ne;
                    </button>
                </template>
                <span class="relative text-xs tabular-nums opacity-70" data-testid="facet-value-count">{{
                    item.count.toLocaleString()
                }}</span>
            </div>
            <button
                v-if="values.length > VISIBLE_VALUES"
                class="pl-4 text-xs text-primary hover:underline"
                @click="showAll = !showAll"
                :data-testid="`facet-more-${id}`"
            >
                {{ showAll ? 'Show less' : `Show ${values.length - VISIBLE_VALUES} more` }}
            </button>
            <div v-if="more && (showAll || values.length <= VISIBLE_VALUES)" class="pl-4 text-xs opacity-60">
                Only the top {{ values.length }} are shown
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { VISIBLE_VALUES, formatValue } from '@/components/explorer/facets/facets'

const props = defineProps({
    id: String,
    title: String,
    kind: { type: String, default: 'value' },
    values: { type: Array, default: () => [] },
    total: { type: Number, default: 0 },
    more: Boolean,
    pinned: Boolean,
    removable: Boolean,
    expandedKeys: { type: Array, default: () => [] },
})
const emit = defineEmits(['include', 'exclude', 'toggleKey', 'togglePin', 'remove'])

const open = ref(true)
const showAll = ref(false)

const shown = computed(() => (showAll.value ? props.values : props.values.slice(0, VISIBLE_VALUES)))

const share = (item) => (props.total ? Math.min(1, item.count / props.total) : 0)

const onClick = (event, item) => {
    if (props.kind === 'keys') emit('toggleKey', item.value)
    else emit(event.altKey ? 'exclude' : 'include', item)
}
</script>
