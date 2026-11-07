// Runs at most `limit` jobs at once; a job whose signal aborted while waiting is skipped.
export function createRequestQueue(limit = 4) {
    let active = 0
    const waiting = []
    const next = () => {
        while (active < limit && waiting.length) {
            const job = waiting.shift()
            if (job.signal?.aborted) {
                job.resolve(null)
                continue
            }
            active++
            job.fn()
                .then(job.resolve, job.reject)
                .finally(() => {
                    active--
                    next()
                })
        }
    }
    return (fn, signal) =>
        new Promise((resolve, reject) => {
            waiting.push({ fn, signal, resolve, reject })
            next()
        })
}
