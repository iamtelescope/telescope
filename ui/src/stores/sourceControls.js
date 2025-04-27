import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { defineStore } from 'pinia'

import { useToast } from 'primevue'

import { DateTime } from 'luxon'

import { Parser as FieldsParser } from '@/utils/fields.js'
import { BoolOperator as FlyQLBoolOperator } from '@/utils/flyql.js'
import { getBooleanFromString } from '@/utils/utils'

import { TelescopeDate, humanRelatedTimeRegex } from '@/utils/datetimeranges.js'

export const useSourceControlsStore = defineStore('sourceDataControls', () => {
    const data = ref({})
    const route = useRoute()
    const toast = useToast()

    const init = computed(() => {
        return (source) => {
            if (route.params.sourceSlug in data.value) {
                throw new Error('Store is already initialized')
            }
            const initData = {
                fields: route.query.fields ?? source.defaultChosenFields.join(', '),
                query: route.query.query ?? '',
                rawQuery: route.query.raw_query ?? '',
                from: route.query.from ?? 'now-5m',
                to: route.query.to ?? 'now',
                graphGroupBy: route.query.graph_group_by ?? source.severityField,
                showGraph: getBooleanFromString(route.query.show_graph, true),
                timezone: 'UTC',
                limit: { value: 50 },
                contextFields: {},
            }
            if (route.query.limit) {
                let intLimit = parseInt(route.query.limit)
                if (!isNaN(intLimit)) {
                    initData.limit = { value: intLimit }
                }
            }
            data.value[route.params.sourceSlug] = initData
            for (const [key, value] of Object.entries(route.query)) {
                if (key.startsWith('ctx')) {
                    let field = key.slice(4)
                    initData.contextFields[field] = value
                }
            }
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
        return new TelescopeDate({
            value: data.value[route.params.sourceSlug].from,
            timezone: data.value[route.params.sourceSlug].timezone,
        })
    })

    const to = computed(() => {
        return new TelescopeDate({
            value: data.value[route.params.sourceSlug].to,
            timezone: data.value[route.params.sourceSlug].timezone,
        })
    })

    const timezone = computed(() => {
        return data.value[route.params.sourceSlug].timezone
    })

    const limit = computed(() => {
        return data.value[route.params.sourceSlug].limit
    })

    const graphGroupBy = computed(() => {
        return data.value[route.params.sourceSlug].graphGroupBy
    })

    const showGraph = computed(() => {
        return data.value[route.params.sourceSlug].showGraph
    })

    const contextFields = computed(() => {
        return data.value[route.params.sourceSlug].contextFields
    })

    const queryParams = computed(() => {
        let params = {
            query: query.value,
            fields: fields.value,
            limit: limit.value.value,
            from: from.value.isRelative ? from.value.value : from.value.dateObj.setZone('UTC').toMillis(),
            to: to.value.isRelative ? to.value.value : to.value.dateObj.setZone('UTC').toMillis(),
            graph_group_by: graphGroupBy.value || '',
            show_graph: showGraph.value,
            context_fields: structuredClone(contextFields.value),
        }
        if (rawQuery.value) {
            params.raw_query = rawQuery.value
        }
        return params
    })

    const queryString = computed(() => {
        let params = []
        for (const [key, value] of Object.entries(queryParams.value)) {
            if (key == 'context_fields') {
                for (const [ctxkey, ctxvalue] of Object.entries(value)) {
                    let k = `ctx_${ctxkey}`
                    for (const i of ctxvalue) {
                        params.push([k, i])
                    }
                }
            } else {
                params.push([key, value])
            }
        }
        return new URLSearchParams(params).toString()
    })

    const dataRequestParams = computed(() => {
        let params = structuredClone(queryParams.value)
        delete params.graph_group_by
        return params
    })

    const graphRequestParams = computed(() => {
        let params = structuredClone(queryParams.value)
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
        if (!humanRelatedTimeRegex.exec(value)) {
            if (value instanceof Date) {
                value = DateTime.fromJSDate(value)
                    .setZone(data.value[route.params.sourceSlug].timezone, { keepLocalTime: true })
                    .toMillis()
            } else {
                let intValue = parseInt(value)
                if (isNaN(intValue)) {
                    value = value.toMillis({ zone: data.value[route.params.sourceSlug].timezone })
                }
            }
        }
        data.value[route.params.sourceSlug].from = value
    }

    function setTo(value) {
        if (!humanRelatedTimeRegex.exec(value)) {
            if (value instanceof Date) {
                value = DateTime.fromJSDate(value)
                    .setZone(data.value[route.params.sourceSlug].timezone, { keepLocalTime: true })
                    .toMillis()
            } else {
                let intValue = parseInt(value)
                if (isNaN(intValue)) {
                    value = value.toMillis({ zone: data.value[route.params.sourceSlug].timezone })
                }
            }
        }
        data.value[route.params.sourceSlug].to = value
    }

    function setTimezone(value) {
        data.value[route.params.sourceSLug].timezone = value
    }

    function setGraphGroupBy(value) {
        data.value[route.params.sourceSlug].graphGroupBy = value
    }

    function setShowGraph(value) {
        data.value[route.params.sourceSlug].showGraph = value
    }

    function setContextField(field, value) {
        data.value[route.params.sourceSlug].contextFields[field] = value
    }

    function addQueryExpression(field, operator, value) {
        let currentQuery = query.value
        if (currentQuery != '') {
            currentQuery += ` ${FlyQLBoolOperator.AND} `
        }
        if (typeof value === 'string') {
            value = '"' + value.replace(/"/g, '\\"') + '"'
        }
        currentQuery += `${field}${operator}${value}`
        data.value[route.params.sourceSlug].query = currentQuery
        toast.add({ severity: 'success', summary: 'Success', detail: 'Query was updated', life: 3000 })
    }

    return {
        init,
        setFields,
        setQuery,
        setRawQuery,
        addQueryExpression,
        setLimit,
        setFrom,
        setTo,
        setTimezone,
        setGraphGroupBy,
        setShowGraph,
        setContextField,
        from,
        to,
        timezone,
        limit,
        fields,
        query,
        rawQuery,
        parsedFields,
        graphGroupBy,
        queryString,
        dataRequestParams,
        graphRequestParams,
        showGraph,
        contextFields,
    }
})
