import HTTP from '@/utils/http'

const http = new HTTP()

class LogsService {
    getLogs = async (slug, params) => {
        let response = await http.Post(`/ui/v1/sources/${slug}/logs`, params)
        return response
    }
}

export { LogsService }