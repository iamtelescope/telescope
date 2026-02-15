const { defineConfig } = require('@vue/cli-service')

const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin')

module.exports = defineConfig({
    outputDir: 'dist',
    assetsDir: 'static',
    publicPath: './',
    transpileDependencies: true,
    devServer: {
        client: false,
        webSocketServer: false,
        proxy: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8000',
        historyApiFallback: true,
    },
    configureWebpack: {
        plugins: [
            new MonacoWebpackPlugin({
                languages: ['json'],
            }),
        ],
    },
})
