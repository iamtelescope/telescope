import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

import "@fontsource/open-sans"
import "@fontsource/open-sans/500.css"

import PrimeVue from 'primevue/config'

import '@/assets/css/main.css'
import 'primeicons/primeicons.css'

import Aura from '@primevue/themes/aura'

const app = createApp(App)

app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            darkModeSelector: '.dark',
            cssLayer: {
                name: 'primevue',
                order: 'tailwind-base, primevue, tailwind-utilities',
            }
        }
    }
})
app.use(router)
app.mount('#app')

