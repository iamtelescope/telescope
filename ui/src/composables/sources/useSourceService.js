import { ref } from 'vue'
import { Source, SourceRoleBiding } from '@/sdk/models/source'
import { SourceService } from '@/sdk/services/source'
import { SavedView } from '@/sdk/models/savedView'

const srv = new SourceService()

const useGetSources = () => {
    const sources = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getSources()
        if (response.result) {
            sources.value = response.data.map((item) => new Source(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { sources, error, loading, load }
}

const useGetSource = (sourceSlug) => {
    const source = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getSource(sourceSlug)
        if (response.result) {
            source.value = new Source(response.data)
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { source, error, loading, load }
}

const useGetSourceRoleBidings = (sourceSlug) => {
    const bindings = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getSourceRoleBindings(sourceSlug)
        if (response.result) {
            bindings.value = response.data.map((item) => new SourceRoleBiding(item))
        }
        error.value = response.errors.join(', ')
        loading.value = false
    }
    load()
    return { bindings, error, loading, load }
}

const useGetSourceData = () => {
    const rows = ref(null)
    const fields = ref(null)
    const error = ref(null)
    const loading = ref(null)
    const validation = ref(null)
    const controller = ref(null)

    const load = async (sourceSlug, params) => {
        loading.value = true
        controller.value = new AbortController()
        let response = await srv.getData(sourceSlug, params, controller.value.signal)
        if (!response.aborted) {
            if (response.result) {
                rows.value = response.data.rows
                fields.value = response.data.fields
            }
            error.value = response.errors.join(', ')
            validation.value = response.validation
        }
        loading.value = false
    }
    return { rows, fields, error, loading, validation, load, controller }
}

const useGetSourceGraphData = () => {
    const data = ref(null)
    const error = ref(null)
    const loading = ref(null)
    const validation = ref(null)
    const controller = ref(null)

    const load = async (sourceSlug, params) => {
        loading.value = true
        controller.value = new AbortController()
        let response = await srv.getGraphData(sourceSlug, params, controller.value.signal)
        if (!response.aborted) {
            if (response.result) {
                data.value = response.data
            }
            error.value = response.errors.join(', ')
            validation.value = response.validation
        }
        loading.value = false
    }
    return { data, error, loading, validation, load, controller }
}

const useGetSourceContextFieldData = () => {
    const data = ref(null)
    const error = ref(null)
    const loading = ref(null)
    const validation = ref(null)

    const load = async (sourceSlug, params) => {
        loading.value = true
        let response = await srv.getContextFieldData(sourceSlug, params)
        if (response.result) {
            data.value = response.data.data
        }
        error.value = response.errors.join(', ')
        validation.value = response.validation
        loading.value = false
    }
    return { data, error, loading, validation, load }
}

const useGetSavedView = (slug, viewSlug) => {
    const savedView = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        if (viewSlug) {
            let response = await srv.getSavedView(slug, viewSlug)
            if (response.result) {
                savedView.value = new SavedView(response.data)
            }
            error.value = response.errors.join(', ')
        }
        loading.value = false
    }
    load()
    return { savedView, error, loading, load }
}

const useGetSavedViews = (slug) => {
    const savedViews = ref(null)
    const loading = ref(null)
    const error = ref(null)

    const load = async () => {
        loading.value = true
        let response = await srv.getSavedViews(slug)
        if (response.result) {
            savedViews.value = response.data.map((item) => new SavedView(item))
        }
        error.value = response.errors.join(', ')

        loading.value = false
    }
    load()
    return { savedViews, error, loading, load }
}

export {
    useGetSource,
    useGetSources,
    useGetSourceRoleBidings,
    useGetSourceData,
    useGetSourceGraphData,
    useGetSourceContextFieldData,
    useGetSavedView,
    useGetSavedViews,
}
