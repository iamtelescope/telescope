<template>
  <div class="flex flex-row">
    <div class="text-3xl font-bold pl-6 pt-6 pb-0 text-nowrap">Delete View</div>
    <div v-if="!deleteInProgress" class="flex flex-row w-full justify-end">
      <i class="pi pi-times hover:cursor-pointer p-4" @click="emitClose"/>
    </div>
  </div>
  <div class="flex flex-col flex-grow p-6 h-full overflow-auto">
    <div class="flex flex-col h-full">
      <div class="flex flex-col h-full justify-end">
        <div> Are you sure you want to delete <span class="font-medium text-sky-600">{{ view.name }}</span> view? This
          action cannot be undone.
        </div>
        <div class="flex flex-row mt-4 w-full justify-end">
          <Button label="Cancel" severity="primary" class="mr-2" text size="small"
                  :disabled="deleteInProgress" @click="emitClose"/>
          <Button label="Delete" severity="danger" icon="pi pi-check" size="small"
                  @click="handleFormSubmit"
                  :loading="deleteInProgress"/>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import {ref} from "vue"
import {Button, useToast} from "primevue"

import {SourceService} from '@/sdk/services/source'

const props = defineProps(['source', 'view'])
const emit = defineEmits(['close', 'deleted', 'actionStarted', 'actionFinished'])
const toast = useToast()
const sourceSrv = new SourceService()

const deleteInProgress = ref(false)

const emitClose = () => {
  emit('close')
}

const handleFormSubmit = async () => {
  emit('actionStarted')
  deleteInProgress.value = true
  let response = await sourceSrv.deleteSavedView(props.source.slug, props.view.slug)
  response.sendToast(toast)
  deleteInProgress.value = false
  emit('actionFinished')
  if (response.result) {
    emit('deleted')
    emitClose()
  }
}
</script>