import { createSSRApp } from "vue";
import App from "./App.vue";
import { handleLuckyBack } from "./composables/lucky";
export function createApp() {
  const app = createSSRApp(App);
  app.mixin({
    onBackPress() {
      return handleLuckyBack();
    },
  });
  return {
    app,
  };
}
