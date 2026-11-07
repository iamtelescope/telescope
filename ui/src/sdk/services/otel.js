import HTTP from '@/utils/http'

const http = new HTTP()

class OtelService {
    detect = async (connectionId, database, table) => {
        return await http.Post('ui/v1/otel/detect', { connection_id: connectionId, database, table })
    }
}

export { OtelService }
