<template>
    <div class="p-2">
        <div class="flex items-center gap-2 mb-2">
            <Skeleton width="5.5rem" height="2rem" borderRadius="6px" />
            <!-- Share URL button -->
            <Skeleton width="6.5rem" height="2rem" borderRadius="6px" />
            <!-- Download button -->
            <Skeleton width="6.5rem" height="2rem" borderRadius="6px" />
            <!-- Limit select -->
            <Skeleton width="5rem" height="2rem" borderRadius="6px" />
            <!-- DateTime picker -->
            <Skeleton width="14rem" height="2rem" borderRadius="6px" />
            <!-- Settings buttons -->
            <Skeleton width="2rem" height="2rem" borderRadius="6px" />
            <Skeleton width="2rem" height="2rem" borderRadius="6px" />
            <div class="flex-1"></div>
            <!-- Saved views -->
            <Skeleton width="8rem" height="2rem" borderRadius="6px" />
            <!-- Show/Hide toggle -->
            <Skeleton width="4.5rem" height="2rem" borderRadius="6px" />
        </div>

        <!-- Context columns skeleton -->
        <div class="flex flex-wrap items-end gap-2 mb-2">
            <Skeleton width="180px" height="2.5rem" borderRadius="6px" />
            <Skeleton width="200px" height="2.5rem" borderRadius="6px" />
            <Skeleton class="flex-1 min-w-[150px]" height="2.5rem" borderRadius="6px" />
            <Skeleton class="flex-1 min-w-[150px]" height="2.5rem" borderRadius="6px" />
        </div>

        <!-- Columns selector skeleton -->
        <div class="mb-2">
            <Skeleton width="100%" height="2.5rem" borderRadius="6px" />
        </div>

        <!-- FlyQL query skeleton -->
        <div class="mb-2">
            <Skeleton width="100%" height="2.5rem" borderRadius="6px" />
        </div>

        <!-- Results table skeleton -->
        <div class="border rounded-lg border-neutral-300 dark:border-neutral-600">
            <div style="height: 2px; width: 100%"></div>
            <div class="p-2">
                <Skeleton width="100%" height="400px" borderRadius="6px" />
            </div>
        </div>
    </div>
</template>

<script setup>
import { Skeleton } from 'primevue'
</script>
