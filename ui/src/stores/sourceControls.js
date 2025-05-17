import {ref, computed} from 'vue'
import {useRoute} from 'vue-router'
import {defineStore} from 'pinia'

import {useToast} from 'primevue'

import {DateTime} from 'luxon'

import {Parser as FieldsParser} from '@/utils/fields.js'
import {BoolOperator as FlyQLBoolOperator} from '@/utils/flyql.js'
import {getBooleanFromString} from '@/utils/utils'

import {TelescopeDate, humanRelatedTimeRegex} from '@/utils/datetimeranges.js'
import * as viewParam from "autoprefixer";

export const useSourceControlsStore = defineStore('sourceDataControls', () => {
    const toast = useToast()
    const route = useRoute()

    const _source = ref(null)
    const _fields = ref(null)
    const _query = ref(null)
    const _rawQuery = ref(null)
    const _from = ref(null)
    const _to = ref(null)
    const _graphGroupBy = ref(null)
    const _showGraph = ref(null)
    const _timezone = ref(null)
    const _limit = ref(null)
    const _contextFields = ref(null)
    const _view = ref(null)

    function $reset() {
        _fields.value = null
        _query.value = null
        _rawQuery.value = null
        _from.value = null
        _to.value = null
        _graphGroupBy.value = null
        _showGraph.value = null
        _timezone.value = null
        _limit.value = null
        _contextFields.value = null
        _view.value = null
    }

    function init(source, viewParam) {
        if (!source) {
            source = _source.value
        } else {
            _source.value = source
        }
        _fields.value = route.query.fields ?? viewParam?.data?.fields ?? source.defaultChosenFields.join(', ')
        _query.value = route.query.query ?? viewParam?.data?.query ?? ''
        _rawQuery.value = route.query.raw_query ?? ''
        _timezone.value = 'UTC'
        _from.value = toTelescopeDate(tryToMillis(route.query.from ?? viewParam?.data?.from ?? 'now'))
        _to.value = toTelescopeDate(tryToMillis(route.query.to ?? viewParam?.data?.to ?? 'now-5m'))
        _graphGroupBy.value = route.query.graph_group_by ?? viewParam?.data?.graph_group_by ?? source.severityField
        _showGraph.value = true
        _limit.value = 50
        _contextFields.value = {}
        _view.value = viewParam

        if (viewParam?.data?.show_graph !== undefined) {
            _showGraph.value = viewParam?.data?.show_graph
        }
        if (route.query.show_graph !== undefined) {
            _showGraph.value = getBooleanFromString(route.query.show_graph, true)
        }
        if (route.query.limit) {
            let intLimit = parseInt(route.query.limit)
            if (!isNaN(intLimit)) {
                _limit.value = intLimit
            }
        } else if (viewParam?.data?.limit) {
            _limit.value = viewParam.data.limit
        }
        for (const [key, value] of Object.entries(route.query)) {
            if (key.startsWith('ctx')) {
                let field = key.slice(4)
                _contextFields.value[field] = value
            }
        }
        if (viewParam?.data?.context_fields) {
            for (const [key, value] of Object.entries(viewParam?.data?.context_fields)) {
                if (!(key in _contextFields.value)) {
                    _contextFields.value[key] = value
                }
            }
        }
    }

    const parsedFields = computed(() => {
        return (source) => {
            const parser = new FieldsParser()
            parser.parse(fields.value, false)
            return parser.getFieldsNames(source, false, 'name')
        }
    })

    const from = computed(() => {
        return _from.value
    })

    const to = computed(() => {
        return _to.value
    })

    const view = computed(() => {
        return _view.value
    })

    const fields = computed(() => {
        return _fields.value
    })

    const query = computed(() => {
        return _query.value
    })

    const rawQuery = computed(() => {
        return _rawQuery.value
    })

    const timezone = computed(() => {
        return _timezone.value
    })

    const limit = computed(() => {
        return _limit.value
    })

    const graphGroupBy = computed(() => {
        return _graphGroupBy.value
    })

    const showGraph = computed(() => {
        return _showGraph.value
    })

    const contextFields = computed(() => {
        return _contextFields.value
    })

    const queryParams = computed(() => {
        let params = {
            fields: fields.value,
            limit: limit.value,
            from: from.value.toRequestRepresentation(),
            to: to.value.toRequestRepresentation(),
            graph_group_by: graphGroupBy.value || '',
            show_graph: showGraph.value,
            context_fields: structuredClone(contextFields.value),
        }
        if (_view.value) {
            params.view = _view.value.slug
        }
        if (_query.value) {
            params.query = _query.value
        }
        if (_rawQuery.value) {
            params.raw_query = _rawQuery.value
        }
        return params
    })

    const routeQuery = computed(() => {
        let params = structuredClone(queryParams.value)

        if (_view.value) {
            const viewData = _view.value.data

            for (const [key, value] of Object.entries(params)) {
                if (key === 'context_fields') {
                    for (const [ctxKey, ctxValue] of Object.entries(value)) {
                        const viewCtxValue = viewData.context_fields?.[ctxKey]
                        if (JSON.stringify(ctxValue) !== JSON.stringify(viewCtxValue)) {
                            params[`ctx_${ctxKey}`] = ctxValue
                        }
                    }
                } else {
                    if (JSON.stringify(value) === JSON.stringify(viewData[key])) {
                        delete params[key]
                    }
                }
            }
        } else {
            for (const [key, value] of Object.entries(params.context_fields)) {
                params[`ctx_${key}`] = value
            }
        }

        delete params.context_fields
        return params
    })

    const queryString = computed(() => {
        return new URLSearchParams(Object.entries(routeQuery.value)).toString()
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

    const viewParams = computed(() => {
        return {
            fields: fields.value,
            query: query.value,
            from: from.value.toRequestRepresentation(),
            to: to.value.toRequestRepresentation(),
            limit: limit.value,
            graph_group_by: graphGroupBy.value,
            show_graph: showGraph.value,
            context_fields: contextFields.value,
        }
    })

    function setView(value) {
        if (!value) {
            resetView()
            return
        }
        _view.value = value
        setFields(value.data.fields)
        setQuery(value.data.query)
        setFrom(value.data.from)
        setTo(value.data.to)
        setLimit(value.data.limit)
        setGraphGroupBy(value.data.graph_group_by)
        setShowGraph(value.data.show_graph)
        setContextFields(value.data.context_fields)
    }

    function resetView() {
        _view.value = null
        $reset()
        init()
    }

    function setFields(value) {
        _fields.value = value
    }

    function setQuery(value) {
        _query.value = value
    }

    function setRawQuery(value) {
        _rawQuery.value = value
    }

    function setLimit(value) {
        _limit.value = value
    }

    function setFrom(value) {
        let newFrom = toTelescopeDate(tryToMillis(value))
        if (newFrom.value !== _from.value.value) {
            _from.value = newFrom
        }
    }

    function setTo(value) {
        let newTo = toTelescopeDate(tryToMillis(value))
        if (newTo.value !== _to.value.value) {
            _to.value = newTo
        }
    }

    function setTimezone(value) {
        _timezone.value = value
    }

    function setGraphGroupBy(value) {
        _graphGroupBy.value = value
    }

    function setShowGraph(value) {
        _showGraph.value = value
    }

    function setContextField(field, value) {
        _contextFields.value[field] = value
    }

    function setContextFields(value) {
        _contextFields.value = value
    }

    function addQueryExpression(field, operator, value) {
        let currentQuery = _query.value
        if (currentQuery !== '') {
            currentQuery += ` ${FlyQLBoolOperator.AND} `
        }
        if (typeof value === 'string') {
            value = '"' + value.replace(/"/g, '\\"') + '"'
        }
        currentQuery += `${field}${operator}${value}`
        setQuery(currentQuery)
        toast.add({severity: 'success', summary: 'Success', detail: 'Query was updated', life: 3000})
    }

    function toTelescopeDate(value) {
        return new TelescopeDate({
            value: value, timezone: _timezone.value,
        })
    }

    function tryToMillis(value) {
        if (!humanRelatedTimeRegex.exec(value)) {
            if (value instanceof Date) {
                value = DateTime.fromJSDate(value)
                    .setZone(_timezone.value, {keepLocalTime: true})
                    .toMillis()
            } else {
                let intValue = parseInt(value)
                if (isNaN(intValue)) {
                    value = value.toMillis({zone: _timezone.value})
                }
            }
        }
        return value
    }

    return {
        init,
        $reset,
        setView,
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
        view,
        timezone,
        limit,
        fields,
        query,
        rawQuery,
        parsedFields,
        graphGroupBy,
        queryString,
        queryParams,
        routeQuery,
        viewParams,
        dataRequestParams,
        graphRequestParams,
        showGraph,
        contextFields,
    }
})
