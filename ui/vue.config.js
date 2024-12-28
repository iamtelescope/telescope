const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  outputDir: 'dist',
  assetsDir: 'static',
  transpileDependencies: true,
  devServer: {
    client: false,
    webSocketServer: false,
    proxy: 'http://127.0.0.1:8000'
  }
})
