<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center">
                        <LayoutDashboard class="mr-3 w-8 h-8" />
                        Dashboards
                    </div>
                </template>
                <template #actions>
                    <Button
                        size="small"
                        severity="secondary"
                        outlined
                        icon="pi pi-upload"
                        label="Import"
                        class="mr-2"
                        @click="openImport"
                    />
                    <Button
                        size="small"
                        severity="secondary"
                        outlined
                        icon="pi pi-th-large"
                        label="From template"
                        class="mr-2"
                        data-testid="dashboards-from-template"
                        @click="router.push({ name: 'dashboardTemplates' })"
                    />
                    <Button size="small" severity="primary" icon="pi pi-plus" label="New" @click="openNew" />
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <ContentBlock header="Dashboards" :collapsible="false">
                        <SkeletonList :columns="5" :rows="10" />
                    </ContentBlock>
                </template>
                <div
                    v-if="!rows.length"
                    class="flex flex-col items-center justify-center text-center py-20 px-4 border border-dashed rounded-lg border-surface-300 dark:border-surface-600"
                    data-testid="dashboards-empty"
                >
                    <div class="flex items-center justify-center w-16 h-16 mb-5 rounded-full bg-highlight">
                        <LayoutDashboard class="w-8 h-8" :stroke-width="1.5" />
                    </div>
                    <div class="text-xl font-medium mb-2">Create your first dashboard</div>
                    <p class="max-w-md mb-6 text-surface-500 dark:text-surface-400">
                        Put charts, numbers and tables from any source side by side, share them with your team and keep
                        an eye on your services.
                    </p>
                    <div class="flex gap-2">
                        <Button size="small" icon="pi pi-plus" label="New dashboard" @click="openNew" />
                        <Button
                            size="small"
                            severity="secondary"
                            outlined
                            icon="pi pi-upload"
                            label="Import JSON"
                            @click="openImport"
                        />
                    </div>
                </div>
                <ContentBlock v-else :collapsible="false">
                    <template #header_text>
                        Dashboards: {{ filteredRows.length
                        }}<span v-if="filteredRows.length !== rows.length" class="text-surface-500"
                            >&nbsp;of {{ rows.length }}</span
                        >
                    </template>
                    <template #actions>
                        <div class="flex items-center gap-2">
                            <IconField>
                                <InputIcon class="pi pi-search" />
                                <InputText
                                    v-model="search"
                                    placeholder="Search dashboards"
                                    size="small"
                                    class="w-64"
                                    data-testid="dashboards-search"
                                />
                            </IconField>
                            <SelectButton
                                v-model="scope"
                                :options="SCOPES"
                                optionLabel="label"
                                optionValue="value"
                                :allowEmpty="false"
                                size="small"
                                data-testid="dashboards-scope"
                            />
                        </div>
                    </template>
                    <DataTable
                        :value="filteredRows"
                        sortField="updatedAt"
                        removableSort
                        size="small"
                        :sortOrder="-1"
                        :paginator="filteredRows.length > 50"
                        :rows="50"
                        :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                        :row-hover="true"
                        data-testid="dashboards-table"
                    >
                        <Column field="name" header="Name" class="font-medium pl-4" :sortable="true">
                            <template #body="{ data }">
                                <router-link
                                    :to="{ name: 'dashboard', params: { dashboardSlug: data.slug } }"
                                    class="table-link"
                                >
                                    {{ data.name }}
                                </router-link>
                                <div
                                    v-if="data.description"
                                    class="text-sm font-normal text-surface-500 dark:text-surface-400 truncate max-w-[40rem]"
                                    :title="data.description"
                                >
                                    {{ data.description }}
                                </div>
                            </template>
                        </Column>
                        <Column field="ownerName" header="Owner" class="w-1 text-nowrap" :sortable="true">
                            <template #body="{ data }">
                                <EmptyValue :value="data.ownerName" />
                                <span v-if="data.mine" class="ml-1 text-surface-500">(you)</span>
                            </template>
                        </Column>
                        <Column field="shared" header="Visibility" class="w-1 text-nowrap" :sortable="true">
                            <template #body="{ data }">
                                <Tag
                                    :icon="data.shared ? 'pi pi-users' : 'pi pi-lock'"
                                    :value="data.shared ? 'Shared' : 'Private'"
                                    :severity="data.shared ? 'success' : 'secondary'"
                                />
                            </template>
                        </Column>
                        <Column field="tilesCount" header="Tiles" class="w-1" :sortable="true" />
                        <Column field="updatedAt" header="Updated" class="w-1 text-nowrap" :sortable="true">
                            <template #body="{ data }">
                                <span :title="fullTime(data.updatedAt)">{{ relativeTime(data.updatedAt) }}</span>
                            </template>
                        </Column>
                        <Column class="w-1 text-nowrap text-right pr-2">
                            <template #body="{ data }">
                                <Button
                                    icon="pi pi-external-link"
                                    text
                                    rounded
                                    size="small"
                                    severity="secondary"
                                    v-tooltip.top="'Open'"
                                    aria-label="Open"
                                    @click="open(data)"
                                />
                                <Button
                                    icon="pi pi-copy"
                                    text
                                    rounded
                                    size="small"
                                    severity="secondary"
                                    v-tooltip.top="'Duplicate'"
                                    aria-label="Duplicate"
                                    :loading="busy === `copy:${data.slug}`"
                                    data-testid="dashboard-duplicate"
                                    @click="duplicate(data)"
                                />
                                <Button
                                    icon="pi pi-download"
                                    text
                                    rounded
                                    size="small"
                                    severity="secondary"
                                    v-tooltip.top="'Export JSON'"
                                    aria-label="Export JSON"
                                    :loading="busy === `export:${data.slug}`"
                                    data-testid="dashboard-export"
                                    @click="exportRow(data)"
                                />
                                <Button
                                    icon="pi pi-trash"
                                    text
                                    rounded
                                    size="small"
                                    severity="danger"
                                    v-tooltip.top="data.canDelete ? 'Delete' : 'Only the owner can delete'"
                                    aria-label="Delete"
                                    :disabled="!data.canDelete"
                                    data-testid="dashboard-delete"
                                    @click="confirmDelete(data)"
                                />
                            </template>
                        </Column>
                        <template #empty>
                            <div class="flex flex-col items-center justify-center py-12 text-surface-500">
                                <i class="pi pi-search text-2xl mb-3 opacity-60" />
                                <p class="font-medium mb-3">No dashboards match these filters</p>
                                <Button label="Clear filters" size="small" text @click="clearFilters" />
                            </div>
                        </template>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>
    <ConfirmDialog group="dashboards-list" />

    <Dialog v-model:visible="newVisible" modal header="New dashboard" :style="{ width: '28rem' }">
        <div class="flex flex-col gap-1">
            <label for="dashboard_name" class="font-medium">Name</label>
            <InputText id="dashboard_name" v-model="newName" autofocus maxlength="255" @keydown.enter="createNew" />
            <ErrorText v-if="newErrors" :text="newErrors" />
        </div>
        <template #footer>
            <Button label="Cancel" severity="secondary" outlined size="small" @click="newVisible = false" />
            <Button label="Create" size="small" :disabled="!newName.trim()" :loading="saving" @click="createNew" />
        </template>
    </Dialog>

    <Dialog v-model:visible="importVisible" modal header="Import dashboard" :style="{ width: '40rem' }">
        <div class="flex flex-col gap-3">
            <input type="file" accept=".json,application/json" @change="onImportFile" data-testid="import-file" />
            <ErrorText v-if="importError" :text="importError" />
            <template v-if="importFile">
                <div class="flex flex-col gap-1">
                    <label class="font-medium">Name</label>
                    <InputText v-model="importName" maxlength="255" />
                </div>
                <div v-if="missingSlugs.length" class="flex flex-col gap-2">
                    <div class="font-medium">These sources do not exist here. Pick a replacement for each:</div>
                    <div v-for="slug in missingSlugs" :key="slug" class="flex items-center gap-2">
                        <span class="w-1/2 truncate font-mono text-sm" :title="slug">{{ slug }}</span>
                        <Select
                            v-model="mapping[slug]"
                            :options="sources || []"
                            optionLabel="name"
                            optionValue="slug"
                            placeholder="Choose a source"
                            filter
                            size="small"
                            class="w-1/2"
                        />
                    </div>
                </div>
                <ValidationError
                    v-if="importValidation && !importValidation.result"
                    :validation="importValidation"
                    message="The server rejected this dashboard"
                />
            </template>
        </div>
        <template #footer>
            <Button label="Cancel" severity="secondary" outlined size="small" @click="importVisible = false" />
            <Button
                label="Import"
                size="small"
                :disabled="!canImport"
                :loading="saving"
                @click="doImport"
                data-testid="import-submit"
            />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { DateTime } from 'luxon'
import {
    Button,
    Column,
    ConfirmDialog,
    DataTable,
    Dialog,
    IconField,
    InputIcon,
    InputText,
    Select,
    SelectButton,
    Tag,
    useConfirm,
    useToast,
} from 'primevue'
import { LayoutDashboard } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import { useGetDashboards, useSaveDashboard } from '@/composables/dashboards/useDashboardService'
import { useGetSources } from '@/composables/sources/useSourceService'
import { Dashboard } from '@/sdk/models/dashboard'
import { DashboardService } from '@/sdk/services/dashboard'
import { useAuthStore } from '@/stores/auth'
import { emptyDashboardData } from '@/utils/dashboards'
import { checkDashboardFile, exportDashboard, fileSourceSlugs, remapSources } from '@/utils/dashboardFile'
import { fieldErrorsText } from '@/utils/utils'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const srv = new DashboardService()
const { user } = storeToRefs(useAuthStore())

const { dashboards, error, loading } = useGetDashboards()
const { sources } = useGetSources()
const { create, remove, loading: saving } = useSaveDashboard()

const SCOPES = [
    { value: 'all', label: 'All' },
    { value: 'mine', label: 'Mine' },
    { value: 'shared', label: 'Shared' },
]
const search = ref('')
const scope = ref('all')
const busy = ref('')

const rows = computed(() =>
    (dashboards.value || []).map((d) => ({
        slug: d.slug,
        name: d.name,
        description: d.description,
        ownerName: d.owner?.username || '',
        mine: !!user.value && d.owner?.username === user.value.username,
        shared: d.shared,
        tilesCount: d.tilesCount,
        updatedAt: d.updatedAt,
        canDelete: d.canDelete(),
    })),
)

const filteredRows = computed(() => {
    const text = search.value.trim().toLowerCase()
    return rows.value.filter((r) => {
        if (scope.value === 'mine' && !r.mine) return false
        if (scope.value === 'shared' && !r.shared) return false
        return !text || `${r.name} ${r.description} ${r.ownerName}`.toLowerCase().includes(text)
    })
})

const clearFilters = () => {
    search.value = ''
    scope.value = 'all'
}

const relativeTime = (value) => DateTime.fromISO(value).toRelative()
const fullTime = (value) => DateTime.fromISO(value).toFormat('yyyy-MM-dd HH:mm:ss ZZZZ')

const open = (row) => router.push({ name: 'dashboard', params: { dashboardSlug: row.slug } })

// The list carries no tile data, so row actions fetch the full dashboard first.
const fetchFull = async (row, action) => {
    busy.value = `${action}:${row.slug}`
    const response = await srv.getDashboard(row.slug)
    busy.value = ''
    if (!response.result) response.sendToastErrors(toast)
    return response.result ? response.data : null
}

const duplicate = async (row) => {
    const full = await fetchFull(row, 'copy')
    if (!full) return
    const created = await create({
        name: `Copy of ${full.name}`,
        description: full.description,
        shared: false,
        data: full.data,
    })
    created.sendToast(toast)
    if (created.result) dashboards.value = [...dashboards.value, new Dashboard(created.data)]
}

const exportRow = async (row) => {
    const full = await fetchFull(row, 'export')
    if (full) exportDashboard(full)
}

const confirmDelete = (row) => {
    confirm.require({
        group: 'dashboards-list',
        header: 'Delete dashboard',
        message: `Delete "${row.name}"? This cannot be undone.`,
        icon: 'pi pi-exclamation-triangle',
        rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true, size: 'small' },
        acceptProps: { label: 'Delete', severity: 'danger', size: 'small' },
        accept: async () => {
            const response = await remove(row.slug)
            response.sendToast(toast)
            if (response.result) dashboards.value = dashboards.value.filter((d) => d.slug !== row.slug)
        },
    })
}

const newVisible = ref(false)
const newName = ref('')
const newErrors = ref('')

const openNew = () => {
    newName.value = ''
    newErrors.value = ''
    newVisible.value = true
}

const createNew = async () => {
    if (!newName.value.trim()) return
    const response = await create({
        name: newName.value.trim(),
        description: '',
        shared: false,
        data: emptyDashboardData(),
    })
    if (response.result) {
        response.sendToastMessages(toast)
        newVisible.value = false
        router.push({ name: 'dashboard', params: { dashboardSlug: response.data.slug }, query: { edit: '1' } })
        return
    }
    newErrors.value = [...response.errors, fieldErrorsText(response.validation?.fields)].filter(Boolean).join('; ')
}

const importVisible = ref(false)
const importFile = ref(null)
const importError = ref('')
const importName = ref('')
const importValidation = ref(null)
const mapping = ref({})

const openImport = () => {
    importFile.value = null
    importError.value = ''
    importValidation.value = null
    mapping.value = {}
    importVisible.value = true
}

const onImportFile = async (event) => {
    importFile.value = null
    importValidation.value = null
    mapping.value = {}
    const file = event.target.files[0]
    if (!file) return
    let parsed
    try {
        parsed = JSON.parse(await file.text())
    } catch (err) {
        importError.value = `Invalid JSON: ${err.message}`
        return
    }
    importError.value = checkDashboardFile(parsed) || ''
    if (importError.value) return
    importFile.value = parsed
    importName.value = parsed.name
}

const missingSlugs = computed(() => {
    if (!importFile.value) return []
    const known = new Set((sources.value || []).map((s) => s.slug))
    return fileSourceSlugs(importFile.value).filter((slug) => !known.has(slug))
})

const canImport = computed(
    () => importFile.value && importName.value.trim() && missingSlugs.value.every((slug) => mapping.value[slug]),
)

const doImport = async () => {
    const response = await create({
        name: importName.value.trim(),
        description: importFile.value.description || '',
        shared: false,
        data: remapSources(importFile.value.data, mapping.value),
    })
    importValidation.value = response.validation
    response.sendToastErrors(toast)
    if (response.result) {
        response.sendToastMessages(toast)
        importVisible.value = false
        router.push({ name: 'dashboard', params: { dashboardSlug: response.data.slug } })
    }
}
</script>
