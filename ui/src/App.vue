<template>
  <Toast class="break-all" />
  <Drawer v-model:visible="sidebarVisible" v-if="isLoggedIn" position="right">
    <template #container>
      <div class="flex flex-col h-full">
        <div class="flex flex-col ">
          <div v-if="user.avatarUrl" class="flex flex-row items-center pl-4 mb-4 pt-3.5 telescope-avatar">
            <Avatar :image="user.avatarUrl" class="avaimg" /> <span class="font-bold text-xl pl-2.5"><i
                v-if="user.type == 'github'" class="pi pi-github text-gray-300"></i> {{ user.username }}</span>
          </div>
          <div v-else class="flex flex-row items-center  pl-4 mb-4 pt-3.5 telescope-avatar">
            <Avatar icon="pi pi-user" /> <span class="font-bold text-xl pl-2.5">{{ user.username }}</span>
          </div>
          <div class="flex flex-col " style="height:100%; padding-top: 15px;">
            <Menu :model="sidebarItems" pt:root:style="border-left:none;border-right: none; border-radius: 0px;" />
          </div>
        </div>
      </div>
    </template>
  </Drawer>
  <div class="flex flex-row align-items-stretch	w-full h-full" v-if="isLoggedIn">
    <div class="flex flex-col items-start w-full h-full">
      <div class="flex flex-row w-full items-center pl-2 pt-2 pb-2 border-b border-neutral-300 dark:border-neutral-600">
        <div class="flex flex-row justify-start align-items-top cursor-pointer" @click="toHome">
          <img src="@/assets/logo.png" height="26px" width="26px"> <span id="logo" class="mr-9 pl-2.5 text-2xl font-bold">Telescope</span>
        </div>
        <div class="flex flex-row w-full justify-start items-center">
          <Breadcrumb :home="home" :model="navStore.items" class="p-2 ml-4"/>
        </div>
        <div class="flex flex-row w-full justify-end items-center mr-4">
          <Button v-if="configStore.config.show_docs_url" icon="pi pi-book" outlined severity="secondary" size="small" class="mr-3" as="a" :href="configStore.config.docs_url" target="_blank" rel="noopener" label="Docs"></Button>
          <Button v-if="configStore.config.show_github_url" icon="pi pi-github" outlined severity="secondary" size="small" class="mr-3" as="a" :href="configStore.config.github_url" target="_blank" rel="noopener" label="GitHub"></Button>
          <Button :icon="themeIcon" outlined severity="secondary" size="small" class="mr-3"
            @click="toggleDark()"></Button>
          <Button v-if="user.hasAccessToSettings()" label="Manage" severity="secondary" icon="pi pi-cog" class="mr-4"
            size="small" outlined @click="toggleManageMenu" aria-haspopup="true" aria-controls="overlay_manage_menu" />
          <Avatar v-if="user.avatarUrl" :image="user.avatarUrl" style="cursor: pointer" class="avaimg"
            @click="sidebarVisible = true"></Avatar>
          <Avatar v-else icon="pi pi-user" style="cursor: pointer" @click="sidebarVisible = true" />
        </div>
        <Menu ref="manageMenu" id="overlay_manage_menu" :model="manageMenuItems" :popup="true" />
      </div>
      <div class="w-full h-full pt-2 pl-2 pr-2 overflow-auto">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>

import { storeToRefs } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import Avatar from 'primevue/avatar'
import Drawer from 'primevue/drawer'
import Menu from 'primevue/menu'
import Button from 'primevue/button'
import Breadcrumb from 'primevue/breadcrumb'

import { useAuthStore } from '@/stores/auth'
import { useNavStore } from '@/stores/nav'
import { useConfigStore } from '@/stores/config'
import { useDark, useToggle } from '@vueuse/core'

const isDark = useDark()
const toggleDark = useToggle(isDark)

const router = useRouter()
const navStore = useNavStore()
const configStore = useConfigStore()
configStore.load()

const { user, isLoggedIn } = storeToRefs(useAuthStore())
const manageMenu = ref();
const manageMenuItems = ref([
  {
    label: 'Role-Based Access Control',
    icon: 'pi pi-shield',
    command: () => {
      router.push({ name: 'rbac' })
    },
  },
])
const toHome = () => {
  window.location = '/'
}
const toggleManageMenu = (event) => {
  manageMenu.value.toggle(event);
};

const home = ref({
  icon: 'pi pi-home',
  url: '/',
});

const themeIcon = computed(() => {
  if (isDark.value) {
    return 'pi pi-sun'
  } else {
    return 'pi pi-moon'
  }
})

const sidebarItems = ref([
  {
    label: 'Account',
    items: [
      {
        label: 'Sign out',
        icon: 'pi pi-sign-out',
        command: () => {
          window.location = `/logout`
        }
      },
    ]
  },
])

const sidebarVisible = ref(false)
</script>