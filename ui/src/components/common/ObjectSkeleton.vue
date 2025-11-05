<template>
    <Tabs value="0">
        <TabList>
            <Tab v-for="(tab, index) in tabs" :key="index" :value="index.toString()">
                {{ tab }}
            </Tab>
        </TabList>
        <TabPanels class="p-0">
            <TabPanel value="0">
                <div class="pt-4">
                    <ContentBlock
                        v-for="(fieldNames, sectionName) in sections"
                        :key="sectionName"
                        :header="sectionName"
                        :class="sectionName !== Object.keys(sections)[0] ? 'mt-6' : ''"
                    >
                        <DataRow
                            v-for="(fieldName, index) in fieldNames"
                            :key="fieldName"
                            :name="fieldName"
                            :copy="false"
                            :showBorder="index !== fieldNames.length - 1"
                        >
                            <div class="flex items-center">
                                <Skeleton width="20rem" height="0.875rem"></Skeleton>
                            </div>
                        </DataRow>
                    </ContentBlock>
                </div>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>

<script setup>
import { Skeleton, Tab, TabList, TabPanel, TabPanels, Tabs } from 'primevue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataRow from '@/components/common/DataRow.vue'

const props = defineProps({
    tabs: {
        type: Array,
        default: () => ['OVERVIEW', 'ACCESS CONTROL'],
    },
    sections: {
        type: Object,
        default: () => ({
            General: ['Id', 'Kind', 'Name', 'Description', 'Created'],
            Data: ['Host', 'Port', 'User', 'SSL', 'Verify'],
        }),
    },
})
</script>
