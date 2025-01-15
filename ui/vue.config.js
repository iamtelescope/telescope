const { defineConfig } = require('@vue/cli-service')

const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin');


module.exports = defineConfig({
  outputDir: 'dist',
  assetsDir: 'static',
  transpileDependencies: true,
  devServer: {
    client: false,
    webSocketServer: false,
    proxy: 'http://127.0.0.1:8000'
  },
  configureWebpack: {
    plugins: [
      new MonacoWebpackPlugin({
        languages: ['json',],
      }),
    ],
  },
})
