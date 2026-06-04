<template>
	<FrappeUIProvider>
		<div class="text-base text-ink-gray-8 h-full bg-surface-white">
			<InstallPrompt v-if="isMobile" />
			<Layout>
				<router-view />
			</Layout>
			<Dialogs />
		</div>
	</FrappeUIProvider>
</template>
<script setup>
import { usersStore } from "@/stores/user";
import { Dialogs } from "@/utils/dialogs";
import { FrappeUIProvider } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import DesktopLayout from "./components/DesktopLayout.vue";
import InstallPrompt from "./components/InstallPrompt.vue";
import MobileLayout from "./components/MobileLayout.vue";
import NoSidebarLayout from "./components/NoSidebarLayout.vue";
import { useScreenSize } from "./utils/composables";

const { isMobile } = useScreenSize();
const router = useRouter();
const noSidebar = ref(false);
const { userResource } = usersStore();

router.beforeEach((to, from, next) => {
	if (
		to.query.fromLesson ||
		to.path === "/persona" ||
		to.path === "/welcome" ||
		to.path === "/login"
	) {
		noSidebar.value = true;
	} else {
		noSidebar.value = false;
	}
	next();
});

const Layout = computed(() => {
	if (noSidebar.value) {
		return NoSidebarLayout;
	}
	if (isMobile.value) {
		return MobileLayout;
	}
	return DesktopLayout;
});

onUnmounted(() => {
	noSidebar.value = false;
});
</script>
