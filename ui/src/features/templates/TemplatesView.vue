<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center gap-3">
                        <router-link
                            :to="{ name: 'dashboards' }"
                            class="text-surface-500 hover:text-primary"
                            title="Dashboards"
                        >
                            <LayoutTemplate class="w-8 h-8" />
                        </router-link>
                        Dashboard templates
                    </div>
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <SkeletonList :columns="3" :rows="4" />
                </template>
                <p class="mb-4 text-surface-500 dark:text-surface-400 max-w-3xl">
                    A template creates a normal dashboard on the sources you pick, one per role. Tiles of an optional
                    role you leave empty are left out; edit the dashboard afterwards like any other.
                </p>
                <div class="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-3" data-testid="templates-gallery">
                    <div
                        v-for="t in templates"
                        :key="t.slug"
                        class="flex flex-col p-4 rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900"
                        :data-testid="`template-${t.slug}`"
                    >
                        <div class="flex items-start justify-between gap-2 mb-2">
                            <div class="text-lg font-medium">{{ t.name }}</div>
                            <span class="text-sm text-nowrap text-surface-500">{{ t.tiles }} tiles</span>
                        </div>
                        <div class="flex flex-wrap gap-1 mb-2">
                            <Tag v-for="tag in t.tags" :key="tag" :value="tag" severity="secondary" />
                        </div>
                        <p class="text-sm text-surface-600 dark:text-surface-300 mb-3 grow">{{ t.description }}</p>
                        <div class="text-sm mb-3 flex flex-wrap gap-x-3 gap-y-1">
                            <span
                                v-for="r in t.roles"
                                :key="r.name"
                                :class="r.candidates.length ? '' : 'text-surface-400 dark:text-surface-500'"
                            >
                                <i
                                    :class="r.candidates.length ? 'pi pi-check text-green-600' : 'pi pi-minus'"
                                    class="text-xs mr-1"
                                />{{ r.label }}<span v-if="r.optional" class="text-surface-500"> (optional)</span>
                            </span>
                        </div>
                        <div class="flex items-center justify-between gap-2">
                            <span v-if="!usable(t)" class="text-sm text-surface-500">No fitting source yet</span>
                            <span v-else />
                            <Button
                                size="small"
                                label="Use template"
                                icon="pi pi-plus"
                                :disabled="!usable(t)"
                                :data-testid="`template-use-${t.slug}`"
                                @click="open(t)"
                            />
                        </div>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
    <Dialog
        v-model:visible="visible"
        modal
        :header="current ? `Create from ${current.name}` : ''"
        :style="{ width: '34rem' }"
        :breakpoints="{ '640px': '95vw' }"
    >
        <div v-if="current" class="flex flex-col gap-4" data-testid="template-dialog">
            <div class="flex flex-col gap-1">
                <label for="template_name" class="font-medium">Name</label>
                <InputText id="template_name" v-model="name" maxlength="255" data-testid="template-name" />
            </div>
            <div v-for="r in current.roles" :key="r.name" class="flex flex-col gap-1">
                <label :for="`role_${r.name}`" class="font-medium">
                    {{ r.label }} source<span v-if="r.optional" class="font-normal text-surface-500"> (optional)</span>
                </label>
                <Select
                    :inputId="`role_${r.name}`"
                    v-model="picks[r.name]"
                    :options="r.candidates"
                    optionLabel="name"
                    optionValue="slug"
                    :placeholder="r.candidates.length ? 'Choose a source' : 'No fitting source'"
                    :disabled="!r.candidates.length"
                    :showClear="r.optional"
                    size="small"
                    :data-testid="`template-role-${r.name}`"
                />
                <small class="text-surface-500">{{ roleHint(r) }}</small>
            </div>
            <div class="flex items-center gap-2">
                <ToggleSwitch v-model="shared" inputId="template_shared" />
                <label for="template_shared">Share with everyone</label>
            </div>
            <ErrorText v-if="problem" :text="problem" data-testid="template-error" />
        </div>
        <template #footer>
            <Button label="Cancel" severity="secondary" outlined size="small" @click="visible = false" />
            <Button
                label="Create dashboard"
                size="small"
                :disabled="!canCreate"
                :loading="saving"
                data-testid="template-create"
                @click="create"
            />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog, InputText, Select, Tag, ToggleSwitch, useToast } from 'primevue'
import { LayoutTemplate } from 'lucide-vue-next'
import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import { TemplateService } from '@/features/templates/service.js'
import { fieldErrorsText } from '@/utils/utils'

const srv = new TemplateService()
const router = useRouter()
const toast = useToast()

const templates = ref([])
const loading = ref(true)
const error = ref(null)
const visible = ref(false)
const current = ref(null)
const name = ref('')
const shared = ref(false)
const picks = reactive({})
const saving = ref(false)
const problem = ref('')

onMounted(async () => {
    const response = await srv.list()
    loading.value = false
    if (response.result) templates.value = response.data
    else error.value = response.errors.join(', ')
})

// Usable when every required role has a source and at least one role can be bound.
const usable = (t) =>
    t.roles.every((r) => r.optional || r.candidates.length) && t.roles.some((r) => r.candidates.length)

const roleHint = (r) => {
    if (r.signal) return `An OTel ${r.signal} source.`
    return r.hint ? `${r.hint}.` : `A source on ${r.table}.`
}

const open = (t) => {
    current.value = t
    name.value = t.name
    shared.value = false
    problem.value = ''
    for (const key of Object.keys(picks)) delete picks[key]
    for (const r of t.roles) picks[r.name] = r.default
    visible.value = true
}

const canCreate = computed(
    () =>
        current.value &&
        name.value.trim() &&
        current.value.roles.every((r) => r.optional || picks[r.name]) &&
        current.value.roles.some((r) => picks[r.name]),
)

const create = async () => {
    saving.value = true
    problem.value = ''
    const sources = Object.fromEntries(Object.entries(picks).filter(([, slug]) => slug))
    const response = await srv.create(current.value.slug, { name: name.value.trim(), shared: shared.value, sources })
    saving.value = false
    if (response.validation && response.validation.result === false) {
        problem.value = [...(response.validation.non_field || []), fieldErrorsText(response.validation.fields)]
            .filter(Boolean)
            .join('; ')
        return
    }
    if (!response.result) {
        problem.value = response.errors.join(', ')
        return
    }
    visible.value = false
    toast.add({ severity: 'success', summary: 'Dashboard created', detail: response.data.name, life: 3000 })
    router.push({ name: 'dashboard', params: { dashboardSlug: response.data.slug } })
}
</script>
