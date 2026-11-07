import HTTP from '@/utils/http'

const http = new HTTP()

// Per-user preferences stored server-side (backend/telescope_prefs), so every browser sees the same ones.
export const getPinnedFacets = (slug) => http.Get(`ui/v1/prefs/pinned-facets/${slug}`)

export const setPinnedFacets = (slug, facets) => http.Post(`ui/v1/prefs/pinned-facets/${slug}`, { facets })

export const getFavoriteDashboards = () => http.Get('ui/v1/prefs/favorites/dashboards')

export const setFavoriteDashboard = (slug, favorite) =>
    favorite
        ? http.Post(`ui/v1/prefs/favorites/dashboards/${slug}`, {})
        : http.Delete(`ui/v1/prefs/favorites/dashboards/${slug}`)
