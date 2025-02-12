import { ref, computed } from "vue"
import { useRoute } from "vue-router"
import { defineStore } from "pinia"

import { useToast } from 'primevue'

import { Parser as FieldsParser } from '@/utils/fields.js'
import { BoolOperator as FlyQLBoolOperator } from '@/utils/flyql.js'

export const useSourceControlsStore = defineStore('sourceDataControls', () => {
    const data = ref({})
    const route = useRoute()
    const toast = useToast()

    const fields = computed(() => {
        if (route.params.sourceSlug in data.value) {
            return data.value[route.params.sourceSlug].fields
        } else {
            return ''
        }
    })

    const query = computed(() => {
        if (route.params.sourceSlug in data.value) {
            return data.value[route.params.sourceSlug].query
        } else {
            return ''
        }
    })

    const parsedFields = computed(() => {
        return (source) => {
            const parser = new FieldsParser()
            parser.parse(fields.value, false)
            return parser.getFieldsNames(source, false, 'name')
        }
    })

    function setFields(value) {
        if (route.params.sourceSlug in data.value) {
            data.value[route.params.sourceSlug].fields = value
        } else {
            data.value[route.params.sourceSlug] = {
                fields: value,
                query: '',
            }
        }
    }

    function setQuery(value) {
        if (route.params.sourceSlug in data.value) {
            data.value[route.params.sourceSlug].query = value
        } else {
            data.value[route.params.sourceSlug] = {
                fields: '',
                query: value,
            }
        }
    }

    function addQueryExpression(field, operator, value) {
        let currentQuery = query.value
        if (currentQuery != "") {
            currentQuery += ` ${FlyQLBoolOperator.AND} `
        }
        if (typeof value === "string") {
            value = '"' + value.replace(/"/g, '\\"') + '"'
        }
        currentQuery += `${field}${operator}${value}`
        data.value[route.params.sourceSlug].query = currentQuery
        toast.add({ severity: 'success', summary: 'Success', detail: 'Query was updated', life: 3000 });
    }

    return { setFields, setQuery, addQueryExpression, fields, query, parsedFields }
})