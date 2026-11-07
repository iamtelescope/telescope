import HTTP from '@/utils/http'

const http = new HTTP()
const qs = (params) =>
    new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')).toString()

export class AlertService {
    list = (params) => http.Get(params ? `ui/v1/alerts?${qs(params)}` : 'ui/v1/alerts')
    get = (id) => http.Get(`ui/v1/alerts/${id}`)
    create = (data) => http.Post('ui/v1/alerts', data)
    update = (id, data) => http.Patch(`ui/v1/alerts/${id}`, data)
    remove = (id) => http.Delete(`ui/v1/alerts/${id}`)
    history = (id, range) => http.Get(range ? `ui/v1/alerts/${id}/history?${qs(range)}` : `ui/v1/alerts/${id}/history`)
    evaluations = (id, params) => http.Get(`ui/v1/alerts/${id}/evaluations?${qs(params)}`)
    silence = (id, until) => http.Post(`ui/v1/alerts/${id}/silenced`, { until })
    unsilence = (id) => http.Delete(`ui/v1/alerts/${id}/silenced`)
    setEnabled = (id, enabled) => http.Post(`ui/v1/alerts/${id}/enabled`, { enabled })
    test = (id) => http.Post(`ui/v1/alerts/${id}/test`)
    markers = (params, signal) => http.Get(`ui/v1/alerts/markers?${qs(params)}`, signal)
    savedViews = (source) => http.Get(`ui/v1/alerts/saved-views/${source}`)
    updateSavedView = (source, id, data) => http.Patch(`ui/v1/alerts/saved-views/${source}/${id}`, data)
    preview = (data, signal) => http.Post('ui/v1/alerts/preview', data, signal)
    channels = () => http.Get('ui/v1/alert-channels')
    createChannel = (data) => http.Post('ui/v1/alert-channels', data)
    updateChannel = (id, data) => http.Patch(`ui/v1/alert-channels/${id}`, data)
    removeChannel = (id) => http.Delete(`ui/v1/alert-channels/${id}`)
    testChannel = (id) => http.Post(`ui/v1/alert-channels/${id}/test`)
}
