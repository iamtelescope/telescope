<template>
    <span :class="['tag', severityClass]">
        {{ value }}
    </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['value', 'severity'])

const severityClass = computed(() => {
    return `tag-${props.severity || 'secondary'}`
})
</script>

<style scoped>
.tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9375rem;
    font-weight: 500;
    line-height: 1.2;
    white-space: nowrap;
    border: 1px solid;
}

.tag-primary {
    background-color: #dbeafe;
    color: #1e40af;
    border-color: #93c5fd;
}

.tag-secondary {
    background-color: #f1f5f9;
    color: #475569;
    border-color: #cbd5e1;
}

.tag-success {
    background-color: #d1fae5;
    color: #065f46;
    border-color: #a7f3d0;
}

.tag-info {
    background-color: #e0f2fe;
    color: #0c4a6e;
    border-color: #7dd3fc;
}

.tag-warn {
    background-color: #fef3c7;
    color: #92400e;
    border-color: #fcd34d;
}

.tag-danger {
    background-color: #fecaca;
    color: #991b1b;
    border-color: #fca5a5;
}

/* Dark mode styles */
:where(.dark, .dark *) .tag-primary {
    background-color: #1e3a8a;
    color: #dbeafe;
    border-color: #1e40af;
}

:where(.dark, .dark *) .tag-secondary {
    background-color: #334155;
    color: #cbd5e1;
    border-color: #475569;
}

:where(.dark, .dark *) .tag-success {
    background-color: #064e3b;
    color: #a7f3d0;
    border-color: #065f46;
}

:where(.dark, .dark *) .tag-info {
    background-color: #0c4a6e;
    color: #7dd3fc;
    border-color: #0369a1;
}

:where(.dark, .dark *) .tag-warn {
    background-color: #92400e;
    color: #fcd34d;
    border-color: #a16207;
}

:where(.dark, .dark *) .tag-danger {
    background-color: #7f1d1d;
    color: #fca5a5;
    border-color: #991b1b;
}
</style>
