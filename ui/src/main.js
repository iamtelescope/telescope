import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import '@fontsource/open-sans'
import '@fontsource/open-sans/500.css'

import PrimeVue from 'primevue/config'

import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

import '@/assets/css/main.css'

import 'primeicons/primeicons.css'
import '@gravity-ui/yagr/dist/index.css'
import 'highlight.js/styles/github.css'

import { library } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faChartArea, faChartLine, faChartColumn } from '@fortawesome/free-solid-svg-icons'
import Aura from '@primevue/themes/aura'

library.add(faChartArea, faChartLine, faChartColumn)

import { initMonacoSetup } from '@/utils/monaco'

import { useAuthStore } from '@/stores/auth.js'

initMonacoSetup()

let appMounted = false
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            darkModeSelector: '.dark',
            cssLayer: {
                name: 'primevue',
                order: 'tailwind-base, primevue, tailwind-utilities',
            },
        },
    },
})
app.use(ConfirmationService)
app.use(ToastService)
app.component('font-awesome-icon', FontAwesomeIcon)
app.directive('tooltip', Tooltip)

const authStore = useAuthStore()
authStore.login()

authStore.$subscribe(() => {
    if (!appMounted) {
        app.use(router)
        app.mount('#app')
        appMounted = true
    } else {
        console.log('app is already mounted')
    }
})
