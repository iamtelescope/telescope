<template>
    <div class="flex flex-col pl-8 pt-6 pr-8 min-h-screen">
        <div>
            <slot name="header"></slot>
        </div>
        <div class="mt-6 w-full">
            <slot name="content"></slot>
        </div>
    </div>
</template>
