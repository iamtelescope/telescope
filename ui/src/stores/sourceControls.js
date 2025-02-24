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

    const init = computed(() => {
        return (source) => {
            if (route.params.sourceSlug in data.value) {
                throw new Error("Store is already initialized");
            }
            const initData = {
                fields: route.query.fields ?? source.defaultChosenFields.join(', '),
                query: route.query.query ?? '',
                from: route.query.from ?? 'now-5m',
                to: route.query.to ?? 'now',
                timezone: 'UTC',
                limit: {"value": 50},
            }
            if (route.query.limit) {
                let intLimit = parseInt(route.query.limit)
                if (!isNaN(intLimit)) {
                    initData.limit = {"value": intLimit}
                }
            }
            data.value[route.params.sourceSlug] = initData
            return true
        }
    })

    const fields = computed(() => {
        return data.value[route.params.sourceSlug].fields
    })

    const query = computed(() => {
        return data.value[route.params.sourceSlug].query
    })

    const parsedFields = computed(() => {
        return (source) => {
            const parser = new FieldsParser()
            parser.parse(fields.value, false)
            return parser.getFieldsNames(source, false, 'name')
        }
    })

    const from = computed(() => {
        return data.value[route.params.sourceSlug].from
    })

    const to = computed(() => {
        return data.value[route.params.sourceSlug].to
    })

    const limit = computed(() => {
        return data.value[route.params.sourceSlug].limit
    })

    function setFields(value) {
        data.value[route.params.sourceSlug].fields = value
    }

    function setQuery(value) {
        data.value[route.params.sourceSlug].query = value
    }

    function setLimit(value) {
        data.value[route.params.sourceSlug].limit = value
    }

    function setFrom(value) {
        data.value[route.params.sourceSlug].from = value
    }

    function setTo(value) {
        data.value[route.params.sourceSlug].to = value
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

    return { init, setFields, setQuery, addQueryExpression, setLimit, setFrom, setTo, from, to, limit, fields, query, parsedFields }
})