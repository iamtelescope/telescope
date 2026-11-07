<template>
    <Button
        icon="pi pi-th-large"
        class="mr-2"
        label="Add to dashboard"
        text
        size="small"
        @click="open"
        data-testid="add-to-dashboard-btn"
    />
    <Dialog v-model:visible="visible" modal header="Add to dashboard" :style="{ width: '30rem' }">
        <div class="flex flex-col gap-3">
            <SelectButton
                v-model="mode"
                :options="modes"
                optionLabel="label"
                optionValue="value"
                :allowEmpty="false"
                size="small"
            />
            <div v-if="mode === 'existing'" class="flex flex-col gap-1">
                <label class="font-medium">Dashboard</label>
                <Select
                    v-model="dashboardSlug"
                    :options="editable"
                    optionLabel="name"
                    optionValue="slug"
                    filter
                    size="small"
                    :loading="loading"
                    placeholder="Choose a dashboard"
                    emptyMessage="No dashboards you can edit"
                />
            </div>
            <div v-else class="flex flex-col gap-1">
                <label class="font-medium">New dashboard name</label>
                <InputText v-model="newName" size="small" maxlength="255" />
            </div>
            <div class="flex flex-col gap-1">
                <label class="font-medium">Tile title</label>
                <InputText v-model="title" size="small" maxlength="128" />
            </div>
            <ErrorText v-if="problem" :text="problem" />
        </div>
        <template #footer>
            <Button label="Cancel" severity="secondary" outlined size="small" @click="visible = false" />
            <Button label="Add" size="small" :disabled="!canAdd" :loading="saving" @click="add" />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button, Dialog, InputText, Select, SelectButton, useToast } from 'primevue'

import ErrorText from '@/components/common/ErrorText.vue'
import { Dashboard } from '@/sdk/models/dashboard'
import { DashboardService } from '@/sdk/services/dashboard'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { bottomY, emptyDashboardData, newTileId } from '@/utils/dashboards'
import { fieldErrorsText } from '@/utils/utils'

const props = defineProps(['source'])

const srv = new DashboardService()
const toast = useToast()
const store = useSourceControlsStore()

const modes = [
    { value: 'existing', label: 'Existing dashboard' },
    { value: 'new', label: 'New dashboard' },
]
const visible = ref(false)
const mode = ref('existing')
const dashboards = ref([])
const loading = ref(false)
const saving = ref(false)
const dashboardSlug = ref(null)
const newName = ref('')
const title = ref('')
const problem = ref('')

const editable = computed(() => dashboards.value.filter((d) => d.canEdit()))
const canAdd = computed(() => (mode.value === 'existing' ? !!dashboardSlug.value : !!newName.value.trim()))

const open = async () => {
    problem.value = ''
    title.value = ''
    visible.value = true
    loading.value = true
    const response = await srv.getDashboards()
    loading.value = false
    dashboards.value = response.result ? response.data.map((d) => new Dashboard(d)) : []
    problem.value = response.errors.join(', ')
    if (!editable.value.length) mode.value = 'new'
}

const buildTile = (tiles) => ({
    id: newTileId(tiles),
    x: 0,
    y: bottomY(tiles),
    w: 12,
    h: 8,
    title: title.value,
    chart: {
        source: props.source.slug,
        display: 'stacked_bar',
        series: [{ agg: 'count' }],
        query: store.query || '',
        raw_query: store.rawQuery || '',
        context_columns: structuredClone(store.contextColumns || {}),
        group_by: store.graphGroupBy || '',
        granularity: 'auto',
        limit: 10,
    },
})

const describe = (response) => {
    const fields = fieldErrorsText(response.validation?.fields)
    return [...response.errors, ...(response.validation?.non_field || []), fields].filter(Boolean).join('; ')
}

const add = async () => {
    problem.value = ''
    saving.value = true
    let response
    if (mode.value === 'new') {
        const data = emptyDashboardData()
        data.tiles.push(buildTile([]))
        response = await srv.createDashboard({ name: newName.value.trim(), description: '', shared: false, data })
    } else {
        response = await srv.getDashboard(dashboardSlug.value)
        if (response.result) {
            const d = response.data
            const data = structuredClone(d.data)
            data.tiles.push(buildTile(data.tiles))
            response = await srv.updateDashboard(d.slug, {
                name: d.name,
                description: d.description,
                shared: d.shared,
                data,
                version: d.version,
            })
        }
    }
    saving.value = false
    if (response.result) {
        toast.add({
            severity: 'success',
            summary: 'Success',
            detail: `Tile added to ${response.data.name}`,
            life: 3000,
        })
        visible.value = false
        return
    }
    // A version conflict means someone saved in between; pressing Add again reloads and retries.
    problem.value = response.validation?.fields?.version
        ? `${response.validation.fields.version.join(', ')}. Press Add to reload and try again.`
        : describe(response)
}
</script>
