<template>
    <!-- renderMarkdown escapes all user HTML before it builds its own tags. -->
    <div class="text-tile-md h-full overflow-auto break-words text-sm leading-relaxed" v-html="html"></div>
</template>

<script setup>
import { computed } from 'vue'

import { renderMarkdown } from '@/components/dashboards/charts/markdown.js'

const props = defineProps(['text'])

const html = computed(() => renderMarkdown(props.text))
</script>

<style>
.text-tile-md > * + * {
    margin-top: 0.5rem;
}
.text-tile-md h1 {
    font-size: 1.25rem;
    font-weight: 600;
}
.text-tile-md h2 {
    font-size: 1.1rem;
    font-weight: 600;
}
.text-tile-md h3,
.text-tile-md h4 {
    font-weight: 600;
}
.text-tile-md ul {
    list-style: disc;
    padding-left: 1.25rem;
}
.text-tile-md ol {
    list-style: decimal;
    padding-left: 1.25rem;
}
.text-tile-md a {
    color: #2a78d6;
    text-decoration: underline;
}
.text-tile-md code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.85em;
    padding: 0.1rem 0.3rem;
    border-radius: 0.25rem;
    background: var(--p-surface-100);
}
.text-tile-md pre {
    padding: 0.5rem 0.75rem;
    border-radius: 0.375rem;
    overflow-x: auto;
    background: var(--p-surface-100);
}
.text-tile-md pre code {
    padding: 0;
    background: none;
}
.text-tile-md blockquote {
    padding-left: 0.75rem;
    border-left: 3px solid var(--p-surface-300);
    color: var(--p-surface-500);
}
.text-tile-md hr {
    border-color: var(--p-surface-200);
}
.dark .text-tile-md code,
.dark .text-tile-md pre {
    background: var(--p-surface-800);
}
.dark .text-tile-md a {
    color: #6da7ec;
}
.dark .text-tile-md blockquote {
    border-color: var(--p-surface-600);
    color: var(--p-surface-400);
}
.dark .text-tile-md hr {
    border-color: var(--p-surface-700);
}
</style>
