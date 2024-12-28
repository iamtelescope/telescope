import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import "@fontsource/open-sans"
import "@fontsource/open-sans/500.css"

import PrimeVue from 'primevue/config'

import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'

import '@/assets/css/tailwind.css'
import '@/assets/css/primetheme.css'
import '@/assets/css/main.css'

import 'primeicons/primeicons.css'
import '@gravity-ui/yagr/dist/index.css';


import { library } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faChartArea, faChartLine, faChartColumn } from '@fortawesome/free-solid-svg-icons'

library.add(faChartArea, faChartLine, faChartColumn)

import { useAuthStore } from '@/stores/auth.js'

let appMounted = false
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(PrimeVue, { theme: 'none' })
app.use(ConfirmationService)
app.use(ToastService)
app.component('font-awesome-icon', FontAwesomeIcon)


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
