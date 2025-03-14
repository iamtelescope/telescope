const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
    outputDir: 'dist',
    assetsDir: 'static',
    transpileDependencies: true,
    devServer: {
        client: false,
        webSocketServer: false,
    },
    
})