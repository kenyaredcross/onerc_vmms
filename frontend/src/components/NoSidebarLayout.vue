<template>
	<div class="relative flex h-full flex-col">
		<div class="h-full flex-1">
			<div class="flex h-screen text-base bg-surface-white">
				<main
					id="scrollContainer"
					tabindex="-1"
					class="w-full overflow-auto focus:outline-none"
				>
					<slot />
				</main>
			</div>
		</div>
	</div>
</template>
