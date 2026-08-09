<template>
	<Teleport to="body">
		<transition
			enter-active-class="transition duration-200 ease-out"
			enter-from-class="opacity-0 -translate-x-3"
			enter-to-class="opacity-100 translate-x-0"
			leave-active-class="transition duration-150 ease-in"
			leave-from-class="opacity-100 translate-x-0"
			leave-to-class="opacity-0 -translate-x-3"
		>
			<div
				v-if="notifications.isPanelOpen"
				ref="panel"
				class="fixed z-50 flex flex-col bg-surface-base"
				:class="
					isMobile
						? 'inset-0'
						: 'inset-y-0 w-[22rem] border-r border-outline-gray-2 shadow-2xl'
				"
				:style="isMobile ? undefined : { left: sidebarWidth }"
				role="dialog"
				:aria-label="__('Notifications')"
			>
				<header
					class="flex items-center justify-between gap-2 border-b border-outline-gray-2 px-4 py-3"
				>
					<div class="flex items-center gap-2">
						<h2 class="text-base-medium text-ink-gray-9">{{ __("Assignments") }}</h2>
						<Badge v-if="notifications.hasUnread" theme="red" variant="subtle">
							{{ notifications.unreadCount }}
						</Badge>
					</div>
					<Button
						variant="ghost"
						:aria-label="__('Close')"
						@click="notifications.closePanel()"
					>
						<template #icon><X class="h-4 w-4 stroke-1.5" /></template>
					</Button>
				</header>

				<div class="flex-1 overflow-y-auto">
					<div v-if="loading" class="space-y-3 p-4">
						<Skeleton v-for="n in 3" :key="n" class="h-14 w-full rounded-lg" />
					</div>

					<ul v-else-if="notifications.hasUnread" class="divide-y divide-outline-gray-1">
						<li v-for="p in notifications.assignments" :key="p.name">
							<router-link
								:to="{
									name: 'DeploymentDetail',
									params: { id: p.deployment_name },
								}"
								class="flex items-start gap-3 px-4 py-3 hover:bg-surface-gray-2"
								@click="notifications.closePanel()"
							>
								<span
									class="mt-1.5 size-2 shrink-0 rounded-full bg-surface-red-5"
								/>
								<span class="min-w-0">
									<span class="block text-base-medium text-ink-gray-8 truncate">
										{{ p.project_name }}
									</span>
									<span class="block text-sm text-ink-gray-5 truncate">
										{{ p.name }}
									</span>
								</span>
							</router-link>
						</li>
					</ul>

					<div
						v-else
						class="flex h-full flex-col items-center justify-center gap-3 px-6 py-16 text-center"
					>
						<div
							class="grid size-12 place-items-center rounded-full bg-surface-gray-2 text-ink-gray-5"
						>
							<BellOff class="size-6 stroke-1.5" />
						</div>
						<div>
							<p class="text-base-medium text-ink-gray-7">
								{{ __("You're all caught up") }}
							</p>
							<p class="mt-1 text-sm text-ink-gray-5">
								{{ __("New deployment assignments will show up here.") }}
							</p>
						</div>
					</div>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<script setup>
import { useNotifications } from "@/stores/notifications";
import { useSidebar } from "@/stores/sidebar";
import { useScreenSize } from "@/utils/composables";
import { onClickOutside } from "@vueuse/core";
import { Badge, Button, Skeleton } from "frappe-ui";
import { BellOff, X } from "lucide-vue-next";
import { computed, ref } from "vue";

const notifications = useNotifications();
const sidebarStore = useSidebar();
const { isMobile } = useScreenSize();
const panel = ref(null);

const sidebarWidth = computed(() => (sidebarStore.sidebarCollapsed ? "3.5rem" : "14rem"));

const loading = computed(
	() => notifications.assignmentsResource.loading && !notifications.assignments.length
);

onClickOutside(panel, () => notifications.closePanel(), {
	ignore: ["#notifications-btn"],
});
</script>
