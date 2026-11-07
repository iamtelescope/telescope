import HTTP from '@/utils/http'

const http = new HTTP()

export class AlertService {
    list = () => http.Get('ui/v1/alerts')
    get = (id) => http.Get(`ui/v1/alerts/${id}`)
    create = (data) => http.Post('ui/v1/alerts', data)
    update = (id, data) => http.Patch(`ui/v1/alerts/${id}`, data)
    remove = (id) => http.Delete(`ui/v1/alerts/${id}`)
    history = (id) => http.Get(`ui/v1/alerts/${id}/history`)
    preview = (data, signal) => http.Post('ui/v1/alerts/preview', data, signal)
    channels = () => http.Get('ui/v1/alert-channels')
    createChannel = (data) => http.Post('ui/v1/alert-channels', data)
    updateChannel = (id, data) => http.Patch(`ui/v1/alert-channels/${id}`, data)
    removeChannel = (id) => http.Delete(`ui/v1/alert-channels/${id}`)
    testChannel = (id) => http.Post(`ui/v1/alert-channels/${id}/test`)
}
