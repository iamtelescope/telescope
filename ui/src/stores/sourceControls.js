import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { defineStore } from 'pinia'

import { useToast } from 'primevue'

import { BoolOperator as FlyQLBoolOperator } from 'flyql'

import { parseColumnNames } from '@/sdk/flyql'
import { getBooleanFromString } from '@/utils/utils'
import { availableTimeZones, localTimeZone } from '@/utils/datetimeranges'
import { LIVE_INTERVALS } from '@/utils/explorerPaging'

const DEFAULT_LIVE_INTERVAL = 5
const RESULTS_MODES = ['rows', 'patterns', 'deltas']
const resultsModeOf = (mode) => (RESULTS_MODES.includes(mode) ? mode : 'rows')
// The deltas outlier selection {column, outlier}, kept as JSON in ?deltas= ('' clears a saved view's).
const parseDeltas = (value) => {
    try {
        return value ? JSON.parse(value) : null
    } catch {
        return null
    }
}

export const useSourceControlsStore = defineStore('sourceDataControls', () => {
    const toast = useToast()
    const route = useRoute()

    const _source = ref(null)
    const _columns = ref(null)
    const _query = ref(null)
    const _rawQuery = ref(null)
    const _text = ref(null)
    const _live = ref(false)
    const _liveInterval = ref(DEFAULT_LIVE_INTERVAL)

    const _from = ref(null)
    const _to = ref(null)
    const _timeZone = ref(null)

    const _graphGroupBy = ref(null)
    const _showGraph = ref(null)
    const _limit = ref(null)
    const _contextColumns = ref(null)
    const _view = ref(null)
    const _resultsMode = ref('rows')
    const _deltas = ref(null)

    function $reset() {
        _columns.value = null
        _query.value = null
        _rawQuery.value = null
        _text.value = null
        _live.value = false
        _liveInterval.value = DEFAULT_LIVE_INTERVAL
        _from.value = null
        _to.value = null
        _timeZone.value = null
        _graphGroupBy.value = null
        _showGraph.value = null
        _limit.value = null
        _contextColumns.value = null
        _view.value = null
        _resultsMode.value = 'rows'
        _deltas.value = null
    }

    function init(source, viewParam) {
        if (!source) {
            source = _source.value
        } else {
            _source.value = source
        }
        _columns.value = route.query.columns ?? viewParam?.data?.columns ?? source.defaultChosenColumns.join(', ')
        _query.value = route.query.query ?? viewParam?.data?.query ?? ''
        _rawQuery.value = route.query.raw_query ?? ''
        _text.value = route.query.text ?? viewParam?.data?.text ?? ''
        _live.value = route.query.live === '1'
        const interval = parseInt(route.query.live_interval)
        _liveInterval.value = LIVE_INTERVALS.includes(interval) ? interval : DEFAULT_LIVE_INTERVAL
        _from.value = tryToMillis(route.query.from ?? viewParam?.data?.from ?? 'now-5m')
        _to.value = tryToMillis(route.query.to ?? viewParam?.data?.to ?? 'now')
        _timeZone.value = route.query.timeZone ?? viewParam?.data?.timeZone ?? localTimeZone
        _graphGroupBy.value = route.query.graph_group_by ?? viewParam?.data?.graph_group_by ?? source.severityColumn
        _showGraph.value = true
        _limit.value = 50
        _contextColumns.value = {}
        _view.value = viewParam
        _resultsMode.value = resultsModeOf(route.query.mode ?? viewParam?.data?.mode)
        _deltas.value =
            route.query.deltas !== undefined ? parseDeltas(route.query.deltas) : (viewParam?.data?.deltas ?? null)

        if (!availableTimeZones.includes(_timeZone.value)) _timeZone.value = localTimeZone

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
                let column = key.slice(4)
                _contextColumns.value[column] = value
            }
        }
        if (viewParam?.data?.context_columns) {
            for (const [key, value] of Object.entries(viewParam?.data?.context_columns)) {
                if (!(key in _contextColumns.value)) {
                    _contextColumns.value[key] = value
                }
            }
        }
    }

    const parsedColumns = computed(() => {
        return (_source) => parseColumnNames(columns.value)
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

    const columns = computed(() => {
        return _columns.value
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

    const text = computed(() => _text.value)
    const live = computed(() => _live.value)
    const liveInterval = computed(() => _liveInterval.value)

    const limit = computed(() => {
        return _limit.value
    })

    const graphGroupBy = computed(() => {
        return _graphGroupBy.value
    })

    const showGraph = computed(() => {
        return _showGraph.value
    })

    const contextColumns = computed(() => {
        return _contextColumns.value
    })

    const routeQuery = computed(() => {
        let params = {
            columns: columns.value,
            limit: limit.value,
            from: from.value,
            to: to.value,
            timeZone: timeZone.value,
            graph_group_by: graphGroupBy.value || '',
            show_graph: showGraph.value,
        }

        if (query.value) params.query = query.value
        if (rawQuery.value) params.raw_query = rawQuery.value
        if (text.value) params.text = text.value

        if (_resultsMode.value !== (view.value?.data.mode ?? 'rows')) params.mode = _resultsMode.value
        if (view.value) {
            params.view = _view.value.slug

            for (const [key, value] of Object.entries(params)) {
                if (JSON.stringify(value) === JSON.stringify(view.value.data[key])) {
                    delete params[key]
                }
            }
        }

        if (JSON.stringify(_deltas.value) !== JSON.stringify(view.value?.data.deltas ?? null))
            params.deltas = _deltas.value ? JSON.stringify(_deltas.value) : ''

        for (const [key, value] of Object.entries(contextColumns.value)) {
            if (!view.value || JSON.stringify(value) !== JSON.stringify(view.value.data.context_columns?.[key]))
                params[`ctx_${key}`] = value
        }
        if (live.value) {
            params.live = '1'
            if (liveInterval.value !== DEFAULT_LIVE_INTERVAL) params.live_interval = liveInterval.value
        }

        return params
    })

    const dataRequestParams = computed(() => {
        let params = {
            columns: columns.value,
            limit: limit.value,
            from: from.value,
            to: to.value,
            context_columns: structuredClone(contextColumns.value),
        }

        if (query.value) params.query = query.value
        if (rawQuery.value) params.raw_query = rawQuery.value
        if (text.value) params.text = text.value

        return params
    })

    const graphRequestParams = computed(() => {
        let params = {
            from: from.value,
            to: to.value,
            group_by: graphGroupBy.value || '',
            context_columns: structuredClone(contextColumns.value),
        }

        if (query.value) params.query = query.value
        if (rawQuery.value) params.raw_query = rawQuery.value
        if (text.value) params.text = text.value

        return params
    })

    const viewParams = computed(() => {
        return {
            columns: columns.value,
            query: query.value,
            text: text.value,
            from: from.value,
            to: to.value,
            timeZone: timeZone.value,
            limit: limit.value,
            graph_group_by: graphGroupBy.value,
            show_graph: showGraph.value,
            context_columns: contextColumns.value,
            mode: _resultsMode.value,
            deltas: _deltas.value,
        }
    })

    function setView(value) {
        if (!value) {
            resetView()
            return
        }
        _view.value = value
        setFields(value.data.columns)
        setQuery(value.data.query)
        setText(value.data.text ?? '')
        setFrom(value.data.from)
        setTo(value.data.to)
        setLimit(value.data.limit)
        setGraphGroupBy(value.data.graph_group_by)
        setShowGraph(value.data.show_graph)
        setContextColumns(value.data.context_columns)
        _resultsMode.value = resultsModeOf(value.data.mode)
        _deltas.value = value.data.deltas ?? null

        // Some old views might not have this
        if (value.data.timeZone) setTimeZone(value.data.timeZone)
    }

    function resetView() {
        _view.value = null
        $reset()
        init()
    }

    function setFields(value) {
        _columns.value = value
    }

    function setQuery(value) {
        _query.value = value
    }

    function setRawQuery(value) {
        _rawQuery.value = value
    }

    function setText(value) {
        _text.value = value
    }

    function setLive(value) {
        _live.value = !!value
    }

    function setLiveInterval(value) {
        _liveInterval.value = value
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

    function setContextColumn(column, value) {
        _contextColumns.value[column] = value
    }

    function setContextColumns(value) {
        _contextColumns.value = value
    }

    function addQueryExpression(column, operator, value) {
        let currentQuery = _query.value
        if (currentQuery !== '') {
            currentQuery += ` ${FlyQLBoolOperator.AND} `
        }
        if (typeof value === 'string') {
            value = '"' + value.replace(/"/g, '\\"') + '"'
        }
        currentQuery += `${column}${operator}${value}`
        setQuery(currentQuery)
        toast.add({ severity: 'success', summary: 'Success', detail: 'Query was updated', life: 3000 })
    }

    function tryToMillis(value) {
        let intValue = parseInt(value)
        if (!isNaN(intValue) && isFinite(intValue)) return intValue

        return value
    }

    return {
        init,
        $reset,
        setView,
        setFields,
        setQuery,
        setRawQuery,
        setText,
        setLive,
        setLiveInterval,
        addQueryExpression,
        setLimit,
        setFrom,
        setTo,
        setTimeZone,
        setGraphGroupBy,
        setShowGraph,
        setContextColumn,
        from,
        to,
        view,
        resultsMode: _resultsMode,
        deltas: _deltas,
        timeZone,
        limit,
        columns,
        query,
        rawQuery,
        text,
        live,
        liveInterval,
        parsedColumns,
        graphGroupBy,
        routeQuery,
        viewParams,
        dataRequestParams,
        graphRequestParams,
        showGraph,
        contextColumns,
    }
})
