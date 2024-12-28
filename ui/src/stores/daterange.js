import { computed } from 'vue'
import { defineStore } from 'pinia'

export const useDaterangeStore = defineStore('daterangestore', () => {
  const from = ref('now-5m')
  const to = ref('now')

  const text = computed(() => {
    return `${from.value} - ${to.value}`
  })
  
  return { from, to, text }
})