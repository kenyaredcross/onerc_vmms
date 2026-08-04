<template>
	<div class="relative flex h-full flex-col">
		<div class="h-full flex-1">
			<div class="flex h-screen text-base bg-surface-white">
				<nav
					:aria-label="__('Main')"
					class="relative block min-h-0 flex-shrink-0 overflow-hidden hover:overflow-auto"
				>
					<AppSidebar />
				</nav>
				<main
					id="scrollContainer"
					tabindex="-1"
					class="w-full overflow-auto mx-auto focus:outline-none"
				>
					<slot />
				</main>
			</div>
		</div>
	</div>
</template>
<script setup>
import AppSidebar from "./AppSidebar.vue";
</script>
