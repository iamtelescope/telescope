import { ref } from 'vue'
import { Dashboard } from '@/sdk/models/dashboard'
import { DashboardService } from '@/sdk/services/dashboard'

const srv = new DashboardService()

const useGetDashboards = () => {
    const dashboards = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getDashboards()
        if (response.result) {
            dashboards.value = response.data.map((item) => new Dashboard(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { dashboards, error, loading, load }
}

const useGetDashboard = (slug) => {
    const dashboard = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getDashboard(slug)
        if (response.result) {
            dashboard.value = new Dashboard(response.data)
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { dashboard, error, loading, load }
}

const useSaveDashboard = () => {
    const loading = ref(false)
    const validation = ref(null)

    const run = async (call) => {
        loading.value = true
        let response = await call()
        validation.value = response.validation
        loading.value = false
        return response
    }
    const create = (data) => run(() => srv.createDashboard(data))
    const update = (slug, data) => run(() => srv.updateDashboard(slug, data))
    const remove = (slug) => run(() => srv.deleteDashboard(slug))
    return { loading, validation, create, update, remove }
}

// Chart data for one tile; `queue` (optional) limits requests in flight per dashboard.
const useChartData = (queue) => {
    const data = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const code = ref(null)
    const validation = ref(null)
    let controller = null

    const abort = () => {
        controller?.abort()
        controller = null
        loading.value = false
    }

    const load = async (sourceSlug, params) => {
        abort()
        const current = new AbortController()
        controller = current
        loading.value = true
        const call = () => srv.getChartData(sourceSlug, params, current.signal)
        const response = queue ? await queue(call, current.signal) : await call()
        if (current.signal.aborted || !response) return
        data.value = response.result ? response.data : null
        error.value = response.errors.join(', ')
        code.value = response.result ? null : response.data?.code || null
        validation.value = response.validation
        loading.value = false
        controller = null
    }
    return { data, loading, error, code, validation, load, abort }
}

export { useGetDashboards, useGetDashboard, useSaveDashboard, useChartData }
