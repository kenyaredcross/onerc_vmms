<template>
	<div class="mx-auto max-w-4xl px-4 py-6 md:py-10 space-y-6">
		<ErrorMessage
			v-if="helpContent.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm"
			:message="__('Failed to load help content')"
		/>

		<template v-else-if="helpContent.data">
			<!-- About -->
			<section
				v-if="about"
				class="bg-white border border-red-200 rounded-2xl shadow-sm p-6 md:p-8"
			>
				<div class="flex items-start gap-4">
					<div
						class="hidden sm:flex items-center justify-center size-12 shrink-0 rounded-full bg-red-50"
					>
						<Info class="size-6 text-red-500" />
					</div>
					<div class="space-y-2">
						<h1 class="text-2xl md:text-3xl font-semibold text-red-600">
							{{ __(about.heading) }}
						</h1>
						<p v-if="about.subheading" class="text-base text-gray-600 leading-6">
							{{ __(about.subheading) }}
						</p>
					</div>
				</div>
				<div
					v-if="about.body"
					class="mt-5 text-gray-700 leading-7 space-y-3 [&_a]:text-red-600 [&_a]:underline [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5"
					v-html="sanitizeRichHtml(about.body)"
				/>
			</section>

			<!-- FAQs -->
			<section class="space-y-4">
				<div
					class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-1"
				>
					<h2 class="text-xl md:text-2xl font-semibold text-gray-800">
						{{ __("Frequently Asked Questions") }}
					</h2>
					<FormControl
						v-if="totalCount"
						v-model="search"
						type="text"
						:placeholder="__('Search questions')"
						class="w-full sm:w-64"
					>
						<template #prefix>
							<Search class="size-4 text-gray-500" />
						</template>
					</FormControl>
				</div>

				<template v-if="visibleCategories.length">
					<div
						v-for="group in visibleCategories"
						:key="group.category"
						class="space-y-2"
					>
						<h3
							class="text-xs font-semibold uppercase tracking-wide text-gray-500 px-1 pt-2"
						>
							{{ __(group.category) }}
						</h3>
						<div
							class="border rounded-2xl bg-white shadow-sm divide-y overflow-hidden"
						>
							<div v-for="faq in group.faqs" :key="faq.name">
								<button
									type="button"
									:aria-expanded="isOpen(faq.name)"
									class="flex w-full items-center justify-between gap-3 p-4 text-left hover:bg-gray-50 transition duration-150"
									@click="toggle(faq.name)"
								>
									<span class="font-medium text-gray-800">
										{{ faq.question }}
									</span>
									<ChevronDown
										class="size-5 shrink-0 text-gray-500 transition-transform duration-300"
										:class="{ 'rotate-180': isOpen(faq.name) }"
									/>
								</button>
								<div
									v-show="isOpen(faq.name)"
									class="px-4 pb-4 text-gray-700 leading-7 space-y-3 [&_a]:text-red-600 [&_a]:underline [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5"
									v-html="sanitizeRichHtml(faq.answer)"
								/>
							</div>
						</div>
					</div>
				</template>

				<div
					v-else-if="search && totalCount"
					class="border rounded-2xl bg-white shadow-sm p-8 text-center"
				>
					<p class="text-gray-700">
						{{ __("No questions match {0}.").format(`"${search}"`) }}
					</p>
				</div>

				<EmptyState v-else :type="__('FAQ')" class="mt-6" />
			</section>
		</template>

		<div v-else class="space-y-4">
			<div class="h-40 rounded-2xl bg-gray-100 animate-pulse" />
			<div class="h-64 rounded-2xl bg-gray-100 animate-pulse" />
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { ErrorMessage, FormControl, createResource } from "frappe-ui";
import { ChevronDown, Info, Search } from "lucide-vue-next";
import { computed, ref } from "vue";
import EmptyState from "../components/EmptyState.vue";
import { sanitizeRichHtml } from "../utils/sanitizeHtml";

const search = ref("");
const openIds = ref(new Set());

const helpContent = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.faq.get_help_content",
	auto: true,
	cache: ["helpContent"],
});

const about = computed(() => helpContent.data?.about);
const categories = computed(() => helpContent.data?.categories || []);

const totalCount = computed(() =>
	categories.value.reduce((count, group) => count + group.faqs.length, 0)
);

const visibleCategories = computed(() => {
	const term = search.value.trim().toLowerCase();
	if (!term) return categories.value;

	return categories.value
		.map((group) => ({
			category: group.category,
			faqs: group.faqs.filter((faq) =>
				`${faq.question} ${stripTags(faq.answer)}`.toLowerCase().includes(term)
			),
		}))
		.filter((group) => group.faqs.length);
});

function stripTags(html) {
	return (html || "").replace(/<[^>]*>/g, " ");
}

function isOpen(name) {
	return openIds.value.has(name);
}

function toggle(name) {
	// Reassign so the computed/template reacts - Set mutations alone are not tracked.
	const next = new Set(openIds.value);
	next.has(name) ? next.delete(name) : next.add(name);
	openIds.value = next;
}

useHead({
	title: "FAQ | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"Answers to common questions about the Kenya Red Cross Volunteer and Member Management portal, including membership, volunteering, events and deployments.",
		},
	],
});
</script>
