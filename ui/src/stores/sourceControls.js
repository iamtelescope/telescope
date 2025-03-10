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
                rawQuery: route.query.raw_query ?? '',
                from: route.query.from ?? 'now-5m',
                to: route.query.to ?? 'now',
                graphGroupBy: route.query.graph_group_by ?? source.severityField,
                timezone: 'UTC',
                limit: { "value": 50 },
            }
            if (route.query.limit) {
                let intLimit = parseInt(route.query.limit)
                if (!isNaN(intLimit)) {
                    initData.limit = { "value": intLimit }
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

    const rawQuery = computed(() => {
        return data.value[route.params.sourceSlug].rawQuery
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

    const graphGroupBy = computed(() => {
        return data.value[route.params.sourceSlug].graphGroupBy
    })

    const queryParams = computed(() => {
        let params = {
            query: query.value,
            fields: fields.value,
            limit: limit.value.value,
            from: new Date(from.value).valueOf() || from.value,
            to: new Date(to.value).valueOf() || to.value,
            graph_group_by: graphGroupBy.value || "",
        }
        if (rawQuery.value) {
            params.raw_query = rawQuery.value
        }
        return params
    })

    const queryString = computed(() => {
        return new URLSearchParams(queryParams.value).toString()
     })

     const dataRequestParams = computed(() => {
        let params = {... queryParams.value}
        delete params.graph_group_by
        return params
     })

     const graphRequestParams = computed(() => {
        let params = {... queryParams.value}
        params.group_by = params.graph_group_by
        delete params.graph_group_by
        delete params.fields
        delete params.limit
        return params
     })

    function setFields(value) {
        data.value[route.params.sourceSlug].fields = value
    }

    function setQuery(value) {
        data.value[route.params.sourceSlug].query = value
    }

    function setRawQuery(value) {
        data.value[route.params.sourceSlug].rawQuery = value
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

    function setGraphGroupBy(value) {
        data.value[route.params.sourceSlug].graphGroupBy = value
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

    return { init, setFields, setQuery, setRawQuery, addQueryExpression, setLimit, setFrom, setTo, setGraphGroupBy, from, to, limit, fields, query, rawQuery, parsedFields, graphGroupBy, queryString, dataRequestParams, graphRequestParams}
})