<template>
  <Toast class="break-all" />
  <Drawer v-model:visible="sidebarVisible" v-if="isLoggedIn" position="right">
    <template #container>
      <div class="flex flex-col h-full">
        <div class="flex flex-col sidebar">
          <div v-if="user.avatarUrl" class="flex flex-row items-center telescope-avatar">
            <Avatar :image="user.avatarUrl" class="avaimg" /> <span class="telescope-sidebar-username"><i
                v-if="user.type == 'github'" class="pi pi-github text-gray-300"></i> {{ user.username }}</span>
          </div>
          <div v-else class="flex flex-row items-center telescope-avatar">
            <Avatar icon="pi pi-user" /> <span class="telescope-sidebar-username">{{ user.username }}</span>
          </div>
          <div class="flex flex-col sidebar-items" style="height:100%; padding-top: 15px;">
            <Menu :model="sidebarItems" pt:root:style="border-left:none;border-right: none; border-radius: 0px;" />
          </div>
        </div>
      </div>
    </template>
  </Drawer>
  <div class="flex flex-row align-items-stretch	w-full h-full content" v-if="isLoggedIn">
    <div class="flex flex-col items-start w-full h-full">
      <div class="data-header flex flex-row w-full items-center">
        <div class="flex flex-row justify-start align-items-top telescope-logo" @click="toHome">
          <img src="@/assets/logo.png" height="26px" width="26px"> <span id="logo" class="mr-9">Telescope</span>
        </div>
        <div class="flex flex-row w-full justify-start items-center">
          <Breadcrumb :home="home" :model="navStore.items" />
        </div>
        <div class="flex flex-row w-full justify-end items-center mr-6">
          <Button v-if="user.hasAccessToSettings()" label="Manage" severity="secondary" icon="pi pi-cog" class="mr-6"
            size="small" outlined @click="toggleManageMenu" aria-haspopup="true" aria-controls="overlay_manage_menu" />
          <Avatar v-if="user.avatarUrl" :image="user.avatarUrl" style="cursor: pointer" class="avaimg"
            @click="sidebarVisible = true"></Avatar>
          <Avatar v-else icon="pi pi-user" style="cursor: pointer" @click="sidebarVisible = true" />
        </div>
        <Menu ref="manageMenu" id="overlay_manage_menu" :model="manageMenuItems" :popup="true" />
      </div>
      <div class="data-content">
        <router-view />
      </div>
    </div>
  </div>
  <div class="flex h-full w-full items-center justify-center login-content" v-else>
    <router-view />
  </div>

</template>

<script setup>

import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import Avatar from 'primevue/avatar'
import Drawer from 'primevue/drawer'
import Menu from 'primevue/menu'
import Button from 'primevue/button'
import Breadcrumb from 'primevue/breadcrumb'

import { useAuthStore } from '@/stores/auth'
import { useNavStore } from '@/stores/nav'
import { useDark, useToggle } from '@vueuse/core'

const isDark = useDark()
const toggleDark = useToggle(isDark)

const router = useRouter()
const navStore = useNavStore()

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

const sidebarItems = ref([
  //  {
  //    label: 'Settings',
  //    items: [
  //      {
  //        'label': 'Theme',
  //        command: () => {
  //          toggleDark()
  //        }
  //      }
  //    ]
  //  },
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
]);

const sidebarVisible = ref(false)
</script>

<style scoped>
.content {
  height: 100%;
}

.p-breadcrumb {
  padding: 5px;
  margin-left: 10px;
}

.data-header {
  width: 100%;
  height: 30xp;
  border-top-left-radius: 10px;
  padding-top: 10px;
  padding-bottom: 10px;
  padding-left: 15px;
  border-bottom: 1px solid #dbdbdb;
}

.router-content {
  width: 100%;
}

.login-content {
  background-color: #141919;
}

.data-content {
  padding-top: 10px;
  width: 100%;
  height: 100%;
  padding-left: 5px;
  padding-right: 5px;
  overflow-y: auto;
}

.telescope-avatar {
  padding-left: 16px;
  padding-top: 13px;
  margin-bottom: 15px;
}

.dropdown-menu[data-bs-popper] {
  top: 90%;
}

#logo {
  font-size: 18px;
  font-weight: bold;
  padding-left: 10px;
}

.telescope-sidebar-username {
  font-size: 18px;
  font-weight: bold;
  padding-left: 10px;
}

.sidebar {
  height: 100%;
  min-height: 100%;
  width: 100%;
  display: flex;
}

.sidebar>.sidebar-items>.item-header {
  color: rgb(99, 99, 99);
  font-weight: 600;
  padding-top: 15px;
  padding-bottom: 15px;
  padding-right: 15px;
  padding-left: 20px;
  font-size: 15px;
}

.sidebar>.sidebar-items>a {
  text-decoration: none;
  color: black;
  padding-top: 15px;
  padding-bottom: 15px;
  padding-right: 15px;
  padding-left: 20px;
}

.sidebar>.sidebar-items>a:hover {
  background-color: #E3EAE8;
}

.telescope-logo {
  cursor: pointer
}
</style>
