import { ref } from 'vue'

// Runs at most `limit` jobs at once; a job whose signal aborted while waiting is skipped.
// `pending` on the returned function counts queued and running jobs.
export function createRequestQueue(limit = 4) {
    let active = 0
    const waiting = []
    const pending = ref(0)
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
    const run = (fn, signal) => {
        pending.value++
        return new Promise((resolve, reject) => {
            waiting.push({ fn, signal, resolve, reject })
            next()
        }).finally(() => pending.value--)
    }
    run.pending = pending
    return run
}
