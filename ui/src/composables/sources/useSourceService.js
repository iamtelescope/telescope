import { ref } from 'vue'
import { Source, SourceRoleBiding } from '@/sdk/models/source'
import { SourceService } from '@/sdk/services/Source'

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

export { useGetSource, useGetSources, useGetSourceRoleBidings }