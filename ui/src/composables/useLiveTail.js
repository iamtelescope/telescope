import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

// Live tail timer, adapted from HyperDX DBSearchPage useLiveUpdate: polls every interval seconds,
// skips ticks while the tab is hidden, a poll is running, the pointer is over the results or the page is scrolled.
const SCROLL_PAUSE_PX = 40

function scrollParent(el) {
    for (let node = el?.parentElement; node; node = node.parentElement) {
        const overflowY = getComputedStyle(node).overflowY
        if (overflowY === 'auto' || overflowY === 'scroll') return node
    }
    return document.scrollingElement || document.documentElement
}

export function useLiveTail({ enabled, intervalSeconds, rootRef, tick }) {
    const hovering = ref(false)
    const scrolled = ref(false)
    const paused = computed(() => hovering.value || scrolled.value)
    let timer = null
    let busy = false
    let scroller = null

    const run = async () => {
        if (!enabled.value || paused.value || document.hidden || busy) return
        busy = true
        try {
            await tick()
        } finally {
            busy = false
        }
    }

    const stop = () => {
        if (timer) clearInterval(timer)
        timer = null
    }

    const start = () => {
        stop()
        timer = setInterval(run, intervalSeconds.value * 1000)
    }

    const onScroll = () => {
        const top = scroller === window ? window.scrollY : scroller?.scrollTop || 0
        if (enabled.value) scrolled.value = top > SCROLL_PAUSE_PX
    }

    const attachScroll = () => {
        scroller?.removeEventListener('scroll', onScroll)
        const found = scrollParent(rootRef.value)
        scroller = found === document.documentElement || found === document.scrollingElement ? window : found
        scroller.addEventListener('scroll', onScroll, { passive: true })
    }

    const onVisibility = () => {
        if (!document.hidden) run()
    }

    const resume = () => {
        hovering.value = false
        scrolled.value = false
        if (scroller === window) window.scrollTo({ top: 0, behavior: 'instant' })
        else scroller?.scrollTo({ top: 0, behavior: 'instant' })
        run()
    }

    watch([enabled, intervalSeconds], () => {
        if (enabled.value) {
            attachScroll()
            start()
        } else {
            stop()
            hovering.value = false
            scrolled.value = false
        }
    })

    onMounted(() => {
        document.addEventListener('visibilitychange', onVisibility)
        if (enabled.value) {
            attachScroll()
            start()
        }
    })

    onBeforeUnmount(() => {
        stop()
        document.removeEventListener('visibilitychange', onVisibility)
        scroller?.removeEventListener('scroll', onScroll)
    })

    return { hovering, scrolled, paused, resume }
}
