<template>
	<ScrollArea class="min-h-0 flex-1" viewport-class="px-4 pb-10 sm:px-[4.4rem] sm:pb-16">
		<slot />
	</ScrollArea>
</template>

<script setup>
import { ScrollArea } from "frappe-ui";
</script>
