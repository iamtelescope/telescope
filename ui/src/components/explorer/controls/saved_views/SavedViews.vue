<template>
    <div>
        <Drawer v-model:visible="savedViewsListVisible" :modal="false" position="right" pt:root:class="w-[650px]">
            <template #container>
                <SavedViewsList
                    :source="source"
                    :view="viewToUpdate"
                    :currentView="currentView"
                    @change="onSavedViewChange"
                />
            </template>
        </Drawer>
        <Dialog class="w-[600px]" v-model:visible="savedViewFormVisible" :modal="true" draggable>
            <template #container="{ closeCallback }">
                <SavedViewForm
                    :source="source"
                    :view="viewToUpdate"
                    @close="closeCallback"
                    @change="onSavedViewChange"
                />
            </template>
        </Dialog>
        <Dialog
            class="w-[400px]"
            v-model:visible="savedViewDeleteDialogVisible"
            :modal="true"
            draggable
            :closable="savedViewDeleteDialogClosable"
            :closeOnEscape="savedViewDeleteDialogClosable"
        >
            <template #container="{ closeCallback }">
                <SavedViewDeleteDialog
                    :source="source"
                    :view="viewToUpdate"
                    @close="closeCallback"
                    @deleted="onSavedViewDelete"
                    @actionStarted="savedViewDeleteDialogClosable = false"
                    @actionFinished="savedViewDeleteDialogClosable = true"
                />
            </template>
        </Dialog>
        <div class="flex flex-row items-center">
            <div class="flex flex-row items-center mr-2 bg-blue-50 dark:bg-gray-800 pt-2 pb-2 pr-3 pl-3 rounded-lg">
                <span
                    class="font-medium text-sm"
                    v-tooltip.left="currentView?.name?.length > 48 ? currentView?.name : ''"
                    :class="{ 'line-through': deleteLoading }"
                    >{{
                        currentView?.name?.length > 48
                            ? currentView.name.slice(0, 45) + '…'
                            : currentView?.name || 'Default view'
                    }}</span
                >
                <span
                    v-if="modified"
                    class="ml-2 text-xs italic text-amber-700 dark:text-amber-300"
                    v-tooltip.bottom="'The search differs from the saved view'"
                    data-testid="saved-view-modified"
                    >modified</span
                >
            </div>
            <Button
                icon="pi pi-ellipsis-v"
                size="small"
                text
                aria-label="View actions"
                aria-haspopup="true"
                v-tooltip.bottom="'Save, rename or reset the view'"
                data-testid="saved-view-actions"
                @click="toggleSavedViewsMenu"
                :loading="deleteLoading || saveLoading"
            />
            <Menu ref="savedViewsMenu" id="saved_views_menu" :model="savedViewMenuItems" :popup="true" />
            <Button
                size="small"
                label="Views"
                icon="pi pi-folder-open"
                text
                @click="savedViewsListVisible = true"
                data-testid="saved-views-btn"
            />
        </div>
    </div>
</template>
<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Button, Drawer, Dialog, Menu, useToast } from 'primevue'

import SavedViewsList from '@/components/explorer/controls/saved_views/SavedViewsList.vue'
import SavedViewForm from '@/components/explorer/controls/saved_views/SavedViewForm.vue'
import SavedViewDeleteDialog from '@/components/explorer/controls/saved_views/SavedViewDeleteDialog.vue'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { SourceService } from '@/sdk/services/source'

const props = defineProps(['source', 'savedView'])
const emit = defineEmits(['change'])
const toast = useToast()
const savedViewsMenu = ref()
const route = useRoute()
const router = useRouter()
const currentView = ref(props.savedView)
const viewToUpdate = ref(null)
const sourceSrv = new SourceService()

const sourceControlsStore = useSourceControlsStore()
const savedViewsListVisible = ref(false)
const savedViewFormVisible = ref(false)
const savedViewDeleteDialogVisible = ref(false)
const savedViewDeleteDialogClosable = ref(true)
const deleteLoading = ref(false)
const saveLoading = ref(false)

const onSavedViewChange = (view) => {
    savedViewsListVisible.value = false
    currentView.value = view
    emit('change', view)
}

const onSavedViewDelete = () => {
    currentView.value = null
    emit('change', null)
    router.push({ path: route.path, query: {} })
}

const toggleSavedViewsMenu = (event) => {
    savedViewsMenu.value.toggle(event)
}

// Only the settings the view stores count: a view saved without a key does not pin it.
const modified = computed(() => {
    const data = currentView.value?.data
    if (!data) return false
    const params = sourceControlsStore.viewParams
    return Object.entries(data).some(
        ([key, value]) => key in params && JSON.stringify(params[key]) !== JSON.stringify(value),
    )
})

const savedViewMenuItems = computed(() => {
    let items = [
        {
            label: 'Save as new view…',
            icon: 'pi pi-plus',
            command: () => {
                viewToUpdate.value = null
                savedViewFormVisible.value = true
            },
        },
    ]
    if (currentView.value !== null) {
        if (currentView.value.isEditable()) {
            items.unshift({
                label: 'Save changes',
                icon: 'pi pi-save',
                command: () => {
                    saveSavedView(currentView.value)
                },
            })
            items.push({
                label: 'Rename or edit…',
                icon: 'pi pi-pencil',
                command: () => {
                    viewToUpdate.value = currentView.value
                    savedViewFormVisible.value = true
                },
            })
        }
        items.push({
            label: 'Reset to default view',
            icon: 'pi pi-refresh',
            command: () => {
                currentView.value = null
                emit('change', null)
                router.push({ path: route.path, query: {} })
            },
        })
        if (currentView.value.isEditable()) {
            items.push({
                label: 'Delete view',
                icon: 'pi pi-trash',
                command: async () => {
                    viewToUpdate.value = currentView.value
                    savedViewDeleteDialogVisible.value = true
                },
            })
        }
    }
    return items
})

const saveSavedView = async (view) => {
    let data = {
        scope: view.scope,
        name: view.name,
        description: view.description,
        shared: view.shared,
        data: sourceControlsStore.viewParams,
    }
    saveLoading.value = true
    let response = await sourceSrv.updateSavedView(props.source.slug, view.slug, data)
    saveLoading.value = false
    response.sendToast(toast)
    if (response.result && response.validation?.result !== false) currentView.value.data = data.data
}

watch(props, () => {
    currentView.value = props.savedView
})
</script>
