<template>
    <div class="flex flex-col w-full">
        <Fieldset class="text-wrap" :class="'mb-9'">
            <template #legend>
                <span class="font-bold">Common data</span>
            </template>
            <div class="flex flex-wrap gap-4">
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <InputText id="slug" v-model="formData['slug']" fluid
                            :invalid="formErrors['slug'] != ''" :disabled="!slugEditable" />
                        <label for="slug">Slug</label>
                    </FloatLabel>
                    <ErrorText :text="formErrors['slug']" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <InputText id="name" v-model="formData['name']" fluid
                            :invalid="formErrors['name'] != ''" />
                        <label for="name">Name</label>
                    </FloatLabel>
                    <ErrorText :text="formErrors['name']" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <InputText id="description" v-model="formData['description']" fluid
                            :invalid="formErrors['description'] != ''" />
                        <label for="description">Description</label>
                    </FloatLabel>
                    <ErrorText :text="formErrors['description']" />
                </div>
            </div>
        </Fieldset>
    </div>
</template>

<script setup>
import { reactive, watch, computed } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Fieldset from 'primevue/fieldset'
import InputText from 'primevue/inputtext'

import ErrorText from '@/components/common/ErrorText.vue'

const emit = defineEmits(['formDataChanged'])
const props = defineProps([
    'source',
    'formErrors',
])

const getInitialFormData = () => {
    let data = {
        'slug': '',
        'name': '',
        'description': '',
    }
    if (props.source) {
        data.slug = props.source.slug
        data.name = props.source.name
        data.description = props.source.description
    }
    return data
}

const slugEditable = computed(() => {
    if (props.source) {
        return false
    } else {
        return true
    }
})

const formData = reactive(getInitialFormData())


watch(formData, () => {
    emit('formDataChanged', formData)
})

emit('formDataChanged', formData)

</script>
