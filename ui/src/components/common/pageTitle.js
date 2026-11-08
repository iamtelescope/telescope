import { ref, watch } from 'vue'

// The browser tab reads "<page> · Telescope". The router sets the page from route meta;
// a view may name it better (a dashboard's name): setPageTitle(name).
const page = ref('')

export const setPageTitle = (title) => {
    page.value = title || ''
}

watch(page, (t) => (document.title = t ? `${t} · Telescope` : 'Telescope'), { immediate: true })
