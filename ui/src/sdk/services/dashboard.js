import HTTP from '@/utils/http'

const http = new HTTP()

class DashboardService {
    getDashboards = async () => {
        return await http.Get('ui/v1/dashboards')
    }
    getDashboard = async (slug) => {
        return await http.Get(`ui/v1/dashboards/${slug}`)
    }
    createDashboard = async (data) => {
        return await http.Post('ui/v1/dashboards', data)
    }
    updateDashboard = async (slug, data) => {
        return await http.Patch(`ui/v1/dashboards/${slug}`, data)
    }
    deleteDashboard = async (slug) => {
        return await http.Delete(`ui/v1/dashboards/${slug}`)
    }
    getChartData = async (sourceSlug, params, signal) => {
        return await http.Post(`ui/v1/sources/${sourceSlug}/chartData`, params, signal)
    }
}

export { DashboardService }
