<template>
	<FrappeUIProvider>
		<a
			href="#scrollContainer"
			class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[1000] focus:rounded-md focus:bg-surface-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-ink-gray-9 focus:shadow-lg focus:ring-2 focus:ring-red-500"
			@click.prevent="focusMainContent"
		>
			{{ __("Skip to main content") }}
		</a>

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

function focusMainContent() {
	const main = document.getElementById("scrollContainer");
	if (!main) return;
	main.focus();
	main.scrollTo?.({ top: 0 });
}
const noSidebar = ref(false);
const { userResource } = usersStore();

router.beforeEach((to, from, next) => {
	if (
		to.query.fromLesson ||
		to.path === "/persona" ||
		to.path === "/welcome" ||
		to.path === "/login" ||
		to.path === "/verify-membership"
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
