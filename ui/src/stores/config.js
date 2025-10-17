import { ref } from 'vue'
import { defineStore } from 'pinia'

import HTTP from '@/utils/http'

const http = new HTTP()

export const useConfigStore = defineStore('config', () => {
    const config = ref({
        show_docs_url: false,
        show_github_url: false,
        github_url: '',
        docs_url: '',
    })

    async function load() {
        let response = await http.Get('ui/v1/config')
        config.value = response.data
    }
    return { config, load }
})
