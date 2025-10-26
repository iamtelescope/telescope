<template>
    <div class="flex flex-col w-full">
        <div class="flex justify-between items-start">
            <div class="flex flex-col">
                <slot name="left"></slot>
            </div>
            <div class="flex">
                <slot name="right"></slot>
            </div>
        </div>
    </div>
</template>
