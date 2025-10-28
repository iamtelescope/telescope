import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { defineStore } from 'pinia'

import { useToast } from 'primevue'

import { Parser as FieldsParser } from '@/utils/fields.js'
import { BoolOperator as FlyQLBoolOperator } from 'flyql'

import { getBooleanFromString } from '@/utils/utils'
import { localTimeZone } from '@/utils/datetimeranges'

export const useSourceControlsStore = defineStore('sourceDataControls', () => {
    const toast = useToast()
    const route = useRoute()

    const _source = ref(null)
    const _fields = ref(null)
    const _query = ref(null)
    const _rawQuery = ref(null)
    
    const _from = ref(null)
    const _to = ref(null)
    const _timeZone = ref(null)

    const _graphGroupBy = ref(null)
    const _showGraph = ref(null)
    const _limit = ref(null)
    const _contextFields = ref(null)
    const _view = ref(null)

    function $reset() {
        _fields.value = null
        _query.value = null
        _rawQuery.value = null
        _from.value = null
        _to.value = null
        _timeZone.value = null
        _graphGroupBy.value = null
        _showGraph.value = null
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
        _from.value = tryToMillis(route.query.from ?? viewParam?.data?.from ?? 'now-5m')
        _to.value = tryToMillis(route.query.to ?? viewParam?.data?.to ?? 'now')
        _timeZone.value = route.query.tz ?? localTimeZone
        _graphGroupBy.value = route.query.graph_group_by ?? viewParam?.data?.graph_group_by ?? source.severityField
        _showGraph.value = true
        _limit.value = 50
        _contextFields.value = {}
        _view.value = viewParam

        if (!Intl.supportedValuesOf('timeZone').includes(_timeZone.value))
            _timeZone.value = localTimeZone

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

    const timeZone = computed(() => {
        return _timeZone.value
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

    const routeQuery = computed(() => {
        let params = {
            fields: fields.value,
            limit: limit.value,
            from: from.value,
            to: to.value,
            tz: timeZone.value,
            graph_group_by: graphGroupBy.value || '',
            show_graph: showGraph.value
        }

        if (query.value) params.query = query.value
        if (rawQuery.value) params.raw_query = rawQuery.value

        if (view.value) {
            params.view = _view.value.slug

            for (const [key, value] of Object.entries(params)) {
                if (JSON.stringify(value) === JSON.stringify(view.value.data[key])) {
                    delete params[key]
                }
            }
        }

        for (const [key, value] of Object.entries(contextFields.value)) {
            if (!view.value || JSON.stringify(value) !== JSON.stringify(view.value.data.context_fields?.[key]))
                params[`ctx_${key}`] = value
        }

        return params
    })

    const dataRequestParams = computed(() => {
        let params = {
            fields: fields.value,
            limit: limit.value,
            from: from.value,
            to: to.value,
            context_fields: structuredClone(contextFields.value),
        }

        if (query.value) params.query = query.value
        if (rawQuery.value) params.raw_query = rawQuery.value

        return params
    })

    const graphRequestParams = computed(() => {
        let params = {
            from: from.value,
            to: to.value,
            group_by: graphGroupBy.value || '',
            context_fields: structuredClone(contextFields.value),
        }
        
        if (query.value) params.query = query.value
        if (rawQuery.value) params.raw_query = rawQuery.value

        return params
    })

    const viewParams = computed(() => {
        return {
            fields: fields.value,
            query: query.value,
            from: from.value,
            to: to.value,
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
        _from.value = tryToMillis(value)
    }

    function setTo(value) {
        _to.value = tryToMillis(value)
    }

    function setTimeZone(value) {
        _timeZone.value = value
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
        toast.add({ severity: 'success', summary: 'Success', detail: 'Query was updated', life: 3000 })
    }

    function tryToMillis(value) {
        let intValue = parseInt(value)
        if (!isNaN(intValue) && isFinite(intValue))
            return intValue

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
        setTimeZone,
        setGraphGroupBy,
        setShowGraph,
        setContextField,
        from,
        to,
        view,
        timeZone,
        limit,
        fields,
        query,
        rawQuery,
        parsedFields,
        graphGroupBy,
        routeQuery,
        viewParams,
        dataRequestParams,
        graphRequestParams,
        showGraph,
        contextFields,
    }
})
