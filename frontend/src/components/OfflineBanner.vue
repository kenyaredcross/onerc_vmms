<template>
	<Transition name="offline-slide">
		<div
			v-if="isOffline"
			class="flex items-center justify-center gap-2 bg-gray-800 px-4 py-2 text-center text-sm font-medium text-white"
			role="status"
			aria-live="polite"
		>
			<CloudOff class="size-4 shrink-0" />
			<span>{{ __("You're offline — showing saved data") }}</span>
		</div>
	</Transition>
</template>

<script setup>
import { CloudOff } from "lucide-vue-next";
import { onMounted, onUnmounted, ref } from "vue";

const isOffline = ref(typeof navigator !== "undefined" && !navigator.onLine);

function goOnline() {
	isOffline.value = false;
}
function goOffline() {
	isOffline.value = true;
}

onMounted(() => {
	window.addEventListener("online", goOnline);
	window.addEventListener("offline", goOffline);
});

onUnmounted(() => {
	window.removeEventListener("online", goOnline);
	window.removeEventListener("offline", goOffline);
});
</script>

<style scoped>
.offline-slide-enter-active,
.offline-slide-leave-active {
	transition: all 0.25s ease;
}
.offline-slide-enter-from,
.offline-slide-leave-to {
	opacity: 0;
	transform: translateY(-100%);
}
</style>
