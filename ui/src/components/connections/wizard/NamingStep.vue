<template>
    <Form
        v-slot="$form"
        ref="formRef"
        :initialValues="initialValues"
        :resolver
        @submit="onFormSubmit"
        class="flex flex-col"
    >
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button type="submit" label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" />
        </div>
        <div class="flex flex-col gap-4">
            <div>
                <label for="name" class="font-medium">Name *</label>
                <InputText name="name" id="name" class="w-full mt-1" fluid />
                <Message v-if="$form.name?.invalid" severity="error" size="small" variant="simple" class="mt-1">
                    {{ $form.name.error?.message }}
                </Message>
            </div>
            <div>
                <label for="description" class="font-medium">Description</label>
                <InputText name="description" id="description" class="w-full mt-1" fluid />
                <Message v-if="$form.description?.invalid" severity="error" size="small" variant="simple" class="mt-1">
                    {{ $form.description.error?.message }}
                </Message>
            </div>
        </div>
    </Form>
</template>

<script setup>
import { ref } from 'vue'
import { Button, InputText, Message } from 'primevue'
import { Form } from '@primevue/forms'

const props = defineProps({
    modelValue: Object,
})
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

const formRef = ref(null)

const initialValues = {
    name: props.modelValue?.name || '',
    description: props.modelValue?.description || '',
}

const resolver = ({ values }) => {
    const errors = {}

    if (!values.name || values.name.trim() === '') {
        errors.name = [{ message: 'Name is required' }]
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
