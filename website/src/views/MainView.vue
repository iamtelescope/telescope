<template>
    <div class="flex items-start justify-center min-h-screen bg-cover bg-center bg-no-repeat bg-fixed"
        :style="{ backgroundImage: `url(${require('@/assets/background.png')})`, backgroundSize: 'cover' }">
        <div class="w-full max-w-[1280px]">
            <div class="fixed top-0 left-0 w-full backdrop-blur-lg z-50 transition-all duration-300 ease-in-out p-3"
                :class="{ 'border-b border-gray-300 border-opacity-100': hasScrolled, 'border-opacity-0 border-transparent': !hasScrolled }">
                <div class="flex flex-row max-w-[1280px] mx-auto items-center ">
                    <div class="flex flex-row justify-start items-center cursor-pointer">
                        <img src="@/assets/logo.png" height="40px" width="40px">
                        <span id="logo" class="mr-9 pl-2.5 text-4xl">Telescope</span>
                    </div>

                    <!-- desktop -->
                    <div class="hidden md:flex flex-row w-full justify-end items-center mr-10">
                        <Button icon="pi pi-list-check" severity="secondary" as="a" class="mr-3"
                            href="https://iamtelescope.github.io/telescope/docs/changelog.html" target="_blank"
                            rel="noopener" label="Changelog"></Button>
                        <Button icon="pi pi-book" severity="secondary" as="a" class="mr-3"
                            href="https://iamtelescope.github.io/telescope/docs" target="_blank" rel="noopener"
                            label="Docs"></Button>
                        <Button icon="pi pi-github" severity="secondary" as="a"
                            href="https://github.com/iamtelescope/telescope" target="_blank" rel="noopener"
                            label="GitHub"></Button>
                    </div>

                    <!-- mobile -->
                    <div class="md:hidden flex w-full justify-end items-center">
                        <Button icon="pi pi-bars" severity="secondary" @click="toggleMenu()" />
                        <Drawer v-model:visible="mobilemenuVisible" class="h-auto" position="top" :pt="{
                            content: { class: 'p-0' },
                        }"><template #container>
                                <div class="flex flex-col">
                                    <div class="flex flex-row pl-3 pt-1 pb-1 pr-1 border-b">
                                        <div class="flex flex-row justify-start items-center cursor-pointer">
                                            <img src="@/assets/logo.png" height="40px" width="40px">
                                            <span id="logo" class="mr-9 pl-2.5 text-4xl">Telescope</span>
                                        </div>
                                        <div class="flex flex-row w-full justify-end items-center">
                                            <i class="pi pi-times p-4 mt-3" style="font-size: 1.2rem"
                                                @click="toggleMenu()" />
                                        </div>
                                    </div>
                                    <div class="text-left w-full pt-5">
                                        <ul class="flex flex-col w-full overflow-hidden p-0">
                                            <li class="px-4 py-3 text-lg cursor-pointer border-b"
                                                @click="goTo('https://iamtelescope.github.io/telescope/docs')">
                                                <i class="pi pi-book mr-2"></i> Docs
                                            </li>
                                            <li class="px-4 py-3 text-lg cursor-pointer border-b"
                                                @click="goTo('https://github.com/iamtelescope/telescope')">
                                                <i class="pi pi-github mr-2"></i> GitHub
                                            </li>
                                            <li class="px-4 py-3 text-lg cursor-pointer"
                                                @click="goTo('https://iamtelescope.github.io/telescope/docs/changelog.html')">
                                                <i class="pi pi-list-check mr-2"></i> Changelog
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </template>
                        </Drawer>
                    </div>
                </div>
            </div>
            <div id="promodata"
                class="flex flex-col items-center text-center w-full justify-center pt-[150px] px-6 space-y-12 mb-20">
                <h1 class="text-5xl font-bold text-gray-900">Open-source web-based <span
                        class="bg-gradient-to-r from-blue-500 to-green-800 bg-clip-text text-transparent">Log Viewer
                    </span>UI</h1>
                <p class="text-xl text-gray-700 max-w-4xl">
                    Simplifies log exploration, making data querying user-friendly and secure.
                    <br>
                    Powered by <img src="@/assets/clickhouse.png" alt="ClickHouse Logo"
                        class="inline-block h-6 w-6 mb-1 ml-1 align-middle"> <a
                        href="https://github.com/ClickHouse/ClickHouse" target="_blank"
                        class="font-bold text-blue-600">ClickHouse</a>.
                </p>
                <div class="flex flex-row space-x-4">
                    <Button label="Live Demo" icon="pi pi-caret-right" severity="primary" class="px-6" as="a"
                        href="https://demo.telescope.humanuser.net" target="_blank" rel="noopener"></Button>
                    <Button label="Watch on YouTube" icon="pi pi-video" severity="secondary" class="px-6" as="a"
                        href="https://www.youtube.com/watch?v=5IItMOXwugY" target="_blank" rel="noopener"></Button>
                </div>

                <Galleria :value="images" :numVisible="5" circular autoPlay :showIndicators="false"
                    :changeItemOnIndicatorHover="true" containerStyle="max-width: 1280px" :showThumbnails="false" :pt="{
                        root: { style: 'border: none;' },
                    }">
                    <template #item="slotProps">
                        <img :src="slotProps.item.itemImageSrc" :alt="slotProps.item.alt"
                            style="width: 100%; display: block;" />
                    </template>
                </Galleria>

                <h2 class="text-3xl font-bold text-gray-900">Features</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
                    <Card class="shadow-lg text-left h-full flex flex-col">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-database text-yellow-600 text-3xl"></i></div>
                            <div class="font-bold">Sources Management</div>
                        </template>
                        <template #content>
                            <div class="text-lg">
                                Manage <span class="font-bold">multiple</span> ClickHouse connections and configure
                                field <span class="font-bold">visibility, autocompletion,
                                    and permissions</span> for precise data control.
                            </div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col ">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-search text-blue-600 text-3xl"></i></div>
                            <div class="font-bold"> Efficient Log Search</div>
                        </template>
                        <template #content>
                            <div class="text-lg"><span class="font-bold">Fast</span> and <span
                                    class="font-bold">precise</span> log
                                searches are enabled through structured filtering, removing the need for raw SQL.</div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-chart-bar text-green-600 text-3xl"></i></div>
                            <div class="font-bold">Data Visualization</div>
                        </template>
                        <template #content>
                            <div class="text-lg">A <span class="font-bold">simple yet effective</span> data
                                visualization allows users
                                to group logs and track trends through an interactive graph for quick analysis.
                            </div>
                        </template>
                    </Card>

                    <Card class="shadow-lg text-left h-full flex flex-col">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-lock text-red-700 text-3xl"></i></div>
                            <div class="font-bold">Security</div>
                        </template>
                        <template #content>
                            <div class="text-lg">
                                Ensure <span class="font-bold">secure access with role-based permissions</span>, GitHub
                                authentication, and controlled query execution to prevent unauthorized data exposure.
                            </div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-bolt text-purple-600 text-3xl"></i></div>
                            <div class="font-bold"> High-Performance Log Exploration</div>
                        </template>
                        <template #content>
                            <div class="text-lg">
                                Experience a <span class="font-bold">lightning-fast UI</span> optimized for seamless
                                navigation, powered by ClickHouse efficient query execution on large datasets.
                            </div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-cog text-teal-600 text-3xl"></i></div>
                            <div class="font-bold">Flexible Data Display and Formatting</div>
                        </template>
                        <template #content>
                            <div class="text-lg">Customize data display with <span class="font-bold">field selection,
                                    formatting
                                    options, and structured query filtering</span> for a tailored log exploration
                                experience.</div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col">
                        <template #title>
                            <div class="pb-2"><i class="pi pi-code text-sky-600 text-3xl"></i></div>
                            <div class="font-bold">True Open Source</div>
                        </template>
                        <template #content>
                            <div class="text-lg">Fully open-source under the <span class="font-bold">MIT license</span>,
                                providing the freedom to <span class="bold">use, modify, and extend without
                                    restrictions</span>.</div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col bg-gray-200">
                        <template #title>
                            <div class="pb-2 flex flex-row"><i class="pi pi-clock text-gray-600 text-3xl pr-4"></i>
                                Coming soon...</div>
                            <div class="font-bold">Saved Searches and Collaboration</div>
                        </template>
                        <template #content>
                            <div class="text-lg">Save <span class="bold">query presets</span> and share log views with
                                teammates for <span class="font-bold">faster troubleshooting</span> and consistency.
                            </div>
                        </template>
                    </Card>
                    <Card class="shadow-lg text-left h-full flex flex-col bg-gray-200">
                        <template #title>
                            <div class="pb-2 flex flex-row"><i class="pi pi-clock text-gray-600 text-3xl pr-4"></i>
                                Coming soon...</div>
                            <div class="font-bold">Live Log Streaming and Real-time Updates</div>
                        </template>
                        <template #content>
                            <div class="text-lg">Continuously <span class="font-bold">stream log updates in
                                    real-time</span> for immediate insights.</div>
                        </template>
                    </Card>
                </div>
            </div>
        </div>
    </div>
</template>


<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

import { Button, Card, Galleria, Drawer } from 'primevue'

const hasScrolled = ref(false)

const mobilemenuVisible = ref(false)

const onScroll = () => {
    hasScrolled.value = window.scrollY > 10;
}

const images = ref([
    { itemImageSrc: "/assets/explorer_light.png", alt: "Explorer Light Theme" },
    //{ itemImageSrc: "/assets/explorer_dark.png", alt: "Explorer Dark Theme" },
])


const toggleMenu = (event) => {
    mobilemenuVisible.value = !mobilemenuVisible.value
}
const goTo = (url) => {
    window.open(url, "_blank");
    menu.value.hide();
};
onMounted(() => {
    window.addEventListener("scroll", onScroll);
})

onUnmounted(() => {
    window.removeEventListener("scroll", onScroll);
})

</script>