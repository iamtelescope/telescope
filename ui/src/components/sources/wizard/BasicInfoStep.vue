<template>
    <Form v-slot="$form" :initialValues="initialValues" :resolver @submit="onFormSubmit" class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button type="submit" label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" />
        </div>
        <div class="flex flex-col gap-1">
            <div>
                <label for="name" class="font-medium">Name *</label>
                <InputText name="name" id="name" class="w-full" fluid />
                <Message v-if="$form.name?.invalid" severity="error" size="small" variant="simple">
                    {{ $form.name.error?.message }}
                </Message>
            </div>
            <div class="pt-2">
                <label for="slug" class="font-medium">Slug *</label>
                <InputText name="slug" id="slug" class="w-full" fluid />
                <Message v-if="$form.slug?.invalid" severity="error" size="small" variant="simple">
                    {{ $form.slug.error?.message }}
                </Message>
            </div>
            <div class="pt-2">
                <label for="description" class="font-medium">Description</label>
                <InputText name="description" id="description" class="w-full" fluid />
                <Message v-if="$form.description?.invalid" severity="error" size="small" variant="simple">
                    {{ $form.description.error?.message }}
                </Message>
            </div>
        </div>
    </Form>
</template>

<script setup>
import { Button, InputText, Message } from 'primevue'
import { Form } from '@primevue/forms'

const props = defineProps(['modelValue'])
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

const initialValues = {
    name: props.modelValue?.name || '',
    slug: props.modelValue?.slug || '',
    description: props.modelValue?.description || '',
}

const resolver = ({ values }) => {
    const errors = {}
    if (!values.name) {
        errors.name = [{ message: 'Name is required' }]
    }
    if (!values.slug) {
        errors.slug = [{ message: 'Slug is required' }]
    } else if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(values.slug)) {
        errors.slug = [{ message: 'Slug must be lowercase letters, numbers, and hyphens only (e.g., my-source-name)' }]
    }
    return { values, errors }
}

const onFormSubmit = ({ valid, values }) => {
    if (valid) {
        emit('update:modelValue', values)
        emit('next')
    }
}
</script>
