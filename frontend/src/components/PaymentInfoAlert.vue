<template>
	<div
		class="p-2 bg-gradient-to-r from-green-50 to-orange-50 border border-green-200 rounded-lg shadow-sm"
	>
		<div class="flex items-start space-x-3">
			<div class="flex-shrink-0">
				<AlertTriangle class="w-6 h-6 text-green-600" />
			</div>
			<div>
				<p class="text-green-700 mb-3">
					{{
						__(
							"Payment initiated successfully. Please complete the payment on your phone and confirm the payment after completing it.",
						)
					}}
				</p>
			</div>
		</div>
	</div>
</template>
<script setup>
import { AlertTriangle } from "lucide-vue-next";
</script>
