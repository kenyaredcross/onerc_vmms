import dayjs from "@/utils/dayjs";
import { createDialog } from "@/utils/dialogs";
import { createHead } from "@vueuse/head";
import { frappeRequest, FrappeUI, pageMetaPlugin, setConfig } from "frappe-ui";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import ProgressSpinner from "./components/Common/ProgressSpinner.vue";
import "./index.css";
import router from "./router";
import { initSocket } from "./socket";
import { usersStore } from "./stores/user";
import translationPlugin from "./translation";
const head = createHead();

let pinia = createPinia();
let app = createApp(App);
setConfig("resourceFetcher", frappeRequest);

app.component("ProgressSpinner", ProgressSpinner);

app.use(head);
app.use(FrappeUI);
app.use(pinia);
app.use(router);
app.use(translationPlugin);
app.use(pageMetaPlugin);
app.provide("$dayjs", dayjs);
app.provide("$socket", initSocket());
app.mount("#app");

const { userResource } = usersStore();
app.provide("$user", userResource);

app.config.globalProperties.$user = userResource;
app.config.globalProperties.$dialog = createDialog;
