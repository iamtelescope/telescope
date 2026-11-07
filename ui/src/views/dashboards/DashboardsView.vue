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
                <ContentBlock :header="`Dashboards: ${rows.length}`" :collapsible="false">
                    <DataTable
                        :value="rows"
                        filterDisplay="row"
                        v-model:filters="filters"
                        sortField="name"
                        removableSort
                        size="small"
                        :sortOrder="1"
                        :paginator="rows.length > 50"
                        :rows="50"
                        :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                        :row-hover="true"
                        data-testid="dashboards-table"
                    >
                        <Column
                            field="name"
                            header="Name"
                            class="text-nowrap font-medium pl-4"
                            :sortable="true"
                            :showFilterMenu="false"
                        >
                            <template #body="slotProps">
                                <router-link
                                    :to="{ name: 'dashboard', params: { dashboardSlug: slotProps.data.slug } }"
                                    class="table-link"
                                >
                                    {{ slotProps.data.name }}
                                </router-link>
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by name"
                                    size="small"
                                    fluid
                                    class="min-w-32"
                                />
                            </template>
                        </Column>
                        <Column
                            field="ownerName"
                            header="Owner"
                            class="w-1 text-nowrap"
                            :sortable="true"
                            :showFilterMenu="false"
                        >
                            <template #body="slotProps">
                                <EmptyValue :value="slotProps.data.ownerName" />
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by owner"
                                    size="small"
                                    fluid
                                    class="min-w-32"
                                />
                            </template>
                        </Column>
                        <Column field="shared" header="Shared" class="w-1" :sortable="true">
                            <template #body="slotProps">
                                <BoolBadge :value="slotProps.data.shared" />
                            </template>
                        </Column>
                        <Column field="tilesCount" header="Tiles" class="w-1" :sortable="true" />
                        <Column field="updatedAt" header="Updated" class="w-1 text-nowrap" :sortable="true">
                            <template #body="slotProps">
                                <DateTimeFormatted :value="slotProps.data.updatedAt" />
                            </template>
                        </Column>
                        <template #empty>
                            <div
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <LayoutDashboard class="w-10 h-10 mb-4 opacity-50" />
                                <p class="text-lg font-medium mb-2">No dashboards found</p>
                            </div>
                        </template>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>

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
import { Button, Column, DataTable, Dialog, InputText, Select, useToast } from 'primevue'
import { FilterMatchMode } from '@primevue/core/api'
import { LayoutDashboard } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'
import BoolBadge from '@/components/common/BoolBadge.vue'
import DateTimeFormatted from '@/components/common/DateTimeFormatted.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import { useGetDashboards, useSaveDashboard } from '@/composables/dashboards/useDashboardService'
import { useGetSources } from '@/composables/sources/useSourceService'
import { emptyDashboardData } from '@/utils/dashboards'
import { checkDashboardFile, fileSourceSlugs, remapSources } from '@/utils/dashboardFile'

const router = useRouter()
const toast = useToast()

const { dashboards, error, loading } = useGetDashboards()
const { sources } = useGetSources()
const { create, loading: saving } = useSaveDashboard()

const filters = ref({
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    ownerName: { value: null, matchMode: FilterMatchMode.CONTAINS },
})

const rows = computed(() =>
    (dashboards.value || []).map((d) => ({
        slug: d.slug,
        name: d.name,
        ownerName: d.owner?.username || '',
        shared: d.shared,
        tilesCount: d.tilesCount,
        updatedAt: d.updatedAt,
    })),
)

const fieldErrorsText = (validation) =>
    Object.entries(validation?.fields || {})
        .map(([k, v]) => `${k}: ${[].concat(v).join(', ')}`)
        .join('; ')

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
    newErrors.value = [...response.errors, fieldErrorsText(response.validation)].filter(Boolean).join('; ')
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
