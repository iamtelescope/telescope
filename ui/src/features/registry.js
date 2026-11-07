// Each ui/src/features/<name>/ may add routes.js and nav.js; both default-export an array.
const collect = (ctx) => ctx.keys().flatMap((key) => ctx(key).default || [])

export const featureRoutes = collect(require.context('.', true, /^\.\/[^/]+\/routes\.js$/))

// Nav entry: { section: 'explore' | 'data', label, to, icon (component), routeNames: [], testid }
export const featureNav = collect(require.context('.', true, /^\.\/[^/]+\/nav\.js$/))
