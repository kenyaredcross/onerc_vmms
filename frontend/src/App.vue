<template>
	<FrappeUIProvider>
		<Layout>
			<div>
				<router-view />
			</div>
		</Layout>
	</FrappeUIProvider>
</template>
<script setup lang="ts">
import FrappeUIProvider from "frappe-ui/src/components/Provider/FrappeUIProvider.vue";
import { computed, onUnmounted, ref } from "vue";
import { useScreenSize } from "./utils/composables";
import { useRouter } from "vue-router";
import { usersStore } from "./stores/user";
import NoSideBarLayout from "./components/NoSideBarLayout.vue";
import MobileLayout from "./components/MobileLayout.vue";
import DesktopLayout from "./components/DesktopLayout.vue";

const { isMobile } = useScreenSize();
const router = useRouter();
const noSidebar = ref(false);
const { userResource } = usersStore();

router.beforeEach((to, from, next) => {
	if (
		to.query.fromLesson ||
		to.path === "/persona" ||
		to.path === "/welcome" ||
		to.path === "/account/login"
	) {
		noSidebar.value = true;
	} else {
		noSidebar.value = false;
	}
	next();
});

const Layout = computed(() => {
	if (noSidebar.value) {
		return NoSideBarLayout;
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
