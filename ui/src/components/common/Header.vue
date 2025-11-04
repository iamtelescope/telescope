<template>
    <div class="flex flex-col w-full">
        <div class="flex justify-between items-start">
            <div class="flex flex-col">
                <div class="text-3xl font-medium flex items-center">
                    <div class="flex items-center">
                        <slot name="title"></slot>
                    </div>
                </div>
            </div>
            <div class="flex">
                <slot name="actions"></slot>
            </div>
        </div>
    </div>
</template>
