<template>
	<Dialog v-model="showDialog">
		<template #body-title>
			<h2 class="text-base font-semibold text-ink-gray-9">{{ __("Install VMMS") }}</h2>
		</template>
		<template #body-content>
			<p class="text-sm text-ink-gray-6">
				{{ __("Get the app on your device for easy access & a better experience!") }}
			</p>
		</template>
		<template #actions>
			<Button variant="solid" theme="red" class="w-full" @click="install">
				<template #prefix>
					<FeatherIcon name="download" class="w-4 h-4" />
				</template>
				{{ __("Install") }}
			</Button>
		</template>
	</Dialog>

	<Popover :show="iosInstallMessage" placement="bottom">
		<template #body>
			<div class="m-3 rounded-xl bg-surface-white border border-outline-gray-1 shadow-lg overflow-hidden">
				<!-- Header -->
				<div class="flex items-center justify-between px-4 py-3 border-b border-outline-gray-1">
					<span class="text-sm font-semibold text-ink-gray-9">
						{{ __("Install VMMS") }}
					</span>
					<button
						class="p-1 rounded-md text-ink-gray-4 hover:text-ink-gray-7 hover:bg-surface-gray-2 transition-colors"
						@click="iosInstallMessage = false"
					>
						<FeatherIcon name="x" class="w-4 h-4" />
					</button>
				</div>

				<!-- Body -->
				<div class="px-4 py-3 space-y-2">
					<p class="text-sm text-ink-gray-7">
						{{ __("Get the app on your iPhone for easy access & a better experience.") }}
					</p>
					<p class="text-sm text-ink-gray-6 flex items-center gap-1 flex-wrap">
						<span>{{ __("Tap") }}</span>
						<FeatherIcon name="share" class="w-4 h-4 text-ink-blue-2 shrink-0" />
						<span>{{ __("then") }}</span>
						<span class="font-medium text-ink-gray-8">{{ __("'Add to Home Screen'") }}</span>
					</p>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { ref } from "vue";
import { Button, Dialog, FeatherIcon, Popover } from "frappe-ui";

const deferredPrompt = ref(null);
const showDialog = ref(false);
const iosInstallMessage = ref(false);

const isIos = () => {
	const userAgent = window.navigator.userAgent.toLowerCase();
	return /iphone|ipad|ipod/.test(userAgent);
};

const isInStandaloneMode = () => "standalone" in window.navigator && window.navigator.standalone;

if (isIos() && !isInStandaloneMode()) iosInstallMessage.value = true;

window.addEventListener("beforeinstallprompt", (e) => {
	e.preventDefault();
	deferredPrompt.value = e;
	if (isIos() && !isInStandaloneMode()) iosInstallMessage.value = true;
	else showDialog.value = true;
});

window.addEventListener("appinstalled", () => {
	showDialog.value = false;
	deferredPrompt.value = null;
});

const install = () => {
	deferredPrompt.value.prompt();
	showDialog.value = false;
};
</script>
