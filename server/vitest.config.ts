import { defineConfig } from "vitest/config"

export default defineConfig({
  test: {
    globals: false,
    environment: "node",
  },
  resolve: {
    extensions: [".ts", ".js"],
    alias: {
      // Handle .js imports that point to .ts source files
    },
  },
})
