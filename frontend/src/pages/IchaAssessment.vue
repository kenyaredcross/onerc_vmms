<template>
	<!-- Loading state -->
	<div v-if="loading" class="max-w-2xl mx-auto py-20 text-center">
		<div class="flex flex-col items-center gap-4">
			<div class="size-10 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
			<p class="text-gray-500">{{ __("Loading assessment...") }}</p>
		</div>
	</div>

	<!-- Not eligible -->
	<div v-else-if="notEligibleReason" class="max-w-2xl mx-auto py-20 px-4 text-center space-y-4">
		<div class="flex items-center justify-center size-16 rounded-full bg-red-50 mx-auto">
			<ShieldX class="size-8 text-red-500" />
		</div>
		<h1 class="text-2xl font-bold text-gray-900">{{ __("ICHA Assessment") }}</h1>
		<p class="text-gray-600">{{ notEligibleMessage }}</p>
		<router-link to="/" class="inline-block mt-2 text-red-600 underline text-sm">
			{{ __("Back to Dashboard") }}
		</router-link>
	</div>

	<!-- Results view -->
	<div v-else-if="result" class="max-w-4xl mx-auto px-4 py-10 space-y-8">
		<div
			v-if="justSubmitted"
			class="text-center py-3 px-4 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm font-medium"
		>
			{{ __("Your assessment has been submitted and recorded.") }}
		</div>
		<ResultSummary :result="result" />
		<AnswerReview :answers="result.answers" />
	</div>

	<!-- Active assessment form -->
	<div v-else-if="questions.length" class="max-w-4xl mx-auto px-4 py-10 space-y-8">
		<!-- Header -->
		<div class="p-6 rounded-xl shadow-sm border border-gray-200 bg-gradient-to-r from-red-50 to-white">
			<h1 class="text-3xl font-bold text-gray-900">
				{{ __("ICHA Research Assistant Assessment") }}
			</h1>
			<p class="mt-2 text-gray-600 text-sm">
				{{ __("Answer all questions to complete the assessment. You can only submit once.") }}
			</p>

			<!-- Step indicator -->
			<div class="mt-4 flex items-center justify-between text-sm">
				<span class="text-gray-500">
					{{ __("Section {0} of {1}", [currentPage + 1, totalPages]) }}
					&nbsp;·&nbsp;
					{{ __("Questions {0}–{1} of {2}", [pageStart + 1, pageEnd, questions.length]) }}
				</span>
				<div class="flex items-center gap-1.5 font-medium" :class="answeredCount === questions.length ? 'text-green-600' : 'text-gray-500'">
					<CheckSquare class="size-4" />
					<span>{{ answeredCount }}/{{ questions.length }} {{ __("answered") }}</span>
				</div>
			</div>

			<!-- Progress bar (overall) -->
			<div class="mt-3 h-2 bg-gray-200 rounded-full overflow-hidden">
				<div
					class="h-full bg-red-500 transition-all duration-300 rounded-full"
					:style="{ width: `${(answeredCount / questions.length) * 100}%` }"
				/>
			</div>

			<!-- Page dots -->
			<div class="mt-3 flex gap-1.5">
				<button
					v-for="p in totalPages"
					:key="p"
					type="button"
					@click="goToPage(p - 1)"
					class="h-2 rounded-full transition-all duration-200"
					:class="[
						p - 1 === currentPage ? 'w-6 bg-red-500' : 'w-2',
						pageAnsweredCount(p - 1) === PAGE_SIZE || (p === totalPages && pageAnsweredCount(p - 1) === questions.length - (p - 1) * PAGE_SIZE)
							? 'bg-green-400'
							: p - 1 < currentPage ? 'bg-gray-400' : 'bg-gray-200',
						p - 1 === currentPage ? '!bg-red-500' : ''
					]"
				/>
			</div>
		</div>

		<!-- Current page questions -->
		<div class="space-y-6">
			<div
				v-for="(question, idx) in pageQuestions"
				:key="question.name"
				:id="`q-${question.name}`"
				class="bg-white rounded-xl border p-6 shadow-sm transition-all"
				:class="
					unansweredHighlight && !answers[question.name]
						? 'border-red-400 ring-1 ring-red-300'
						: 'border-gray-200'
				"
			>
				<div class="flex items-center gap-2 mb-3">
					<span class="text-xs font-semibold uppercase tracking-wide text-gray-400">{{ question.course }}</span>
					<span class="text-xs text-gray-300">·</span>
					<span class="text-xs text-gray-400">Q{{ pageStart + idx + 1 }}</span>
				</div>
				<p class="font-semibold text-gray-900 mb-4 leading-snug">
					{{ question.question }}
				</p>
				<div class="space-y-2">
					<label
						v-for="opt in ['A', 'B', 'C', 'D']"
						:key="opt"
						class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors select-none"
						:class="
							answers[question.name] === opt
								? 'border-red-500 bg-red-50'
								: 'border-gray-200 hover:bg-gray-50 hover:border-gray-300'
						"
					>
						<input
							type="radio"
							:name="question.name"
							:value="opt"
							v-model="answers[question.name]"
							class="mt-0.5 shrink-0 accent-red-600"
						/>
						<span class="text-sm text-gray-800 leading-snug">
							<strong class="mr-1">{{ opt }}.</strong>{{ question[`option_${opt.toLowerCase()}`] }}
						</span>
					</label>
				</div>
			</div>
		</div>

		<!-- Unanswered warning -->
		<div
			v-if="unansweredHighlight && pageUnanswered > 0"
			class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
		>
			{{ __("Please answer all questions on this page before continuing. {0} question(s) remaining.", [pageUnanswered]) }}
		</div>

		<!-- Error -->
		<div v-if="submitError" class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
			{{ submitError }}
		</div>

		<!-- Navigation buttons -->
		<div class="flex items-center justify-between pb-12">
			<button
				v-if="currentPage > 0"
				type="button"
				@click="goToPage(currentPage - 1)"
				class="px-6 py-3 rounded-xl font-semibold border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
			>
				{{ __("Back") }}
			</button>
			<div v-else />

			<!-- Continue (not last page) -->
			<button
				v-if="currentPage < totalPages - 1"
				type="button"
				@click="handleContinue"
				class="px-8 py-3 rounded-xl font-semibold text-white bg-red-600 hover:bg-red-700 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
			>
				{{ __("Continue") }}
				<span class="ml-1 text-red-200 text-sm">({{ pageStart + PAGE_SIZE + 1 }}–{{ Math.min(pageStart + PAGE_SIZE * 2, questions.length) }})</span>
			</button>

			<!-- Submit (last page) -->
			<button
				v-else
				type="button"
				:disabled="submitting"
				@click="handleSubmit"
				class="px-8 py-3 rounded-xl font-semibold text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
				:class="submitting ? 'bg-red-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700 cursor-pointer'"
			>
				<span v-if="submitting" class="flex items-center gap-2">
					<span class="size-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
					{{ __("Submitting...") }}
				</span>
				<span v-else>{{ __("Submit Assessment") }}</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui";
import { CheckSquare, ShieldX } from "lucide-vue-next";
import { computed, nextTick, reactive, ref } from "vue";

import AnswerReview from "../components/IchaAssessment/AnswerReview.vue";
import ResultSummary from "../components/IchaAssessment/ResultSummary.vue";

const PAGE_SIZE = 5;

const loading = ref(true);
const notEligibleReason = ref(null);
const questions = ref([]);
const answers = reactive({});
const result = ref(null);
const submitting = ref(false);
const submitError = ref(null);
const unansweredHighlight = ref(false);
const justSubmitted = ref(false);
const currentPage = ref(0);

// Pagination
const totalPages = computed(() => Math.ceil(questions.value.length / PAGE_SIZE));
const pageStart = computed(() => currentPage.value * PAGE_SIZE);
const pageEnd = computed(() => Math.min(pageStart.value + PAGE_SIZE, questions.value.length));
const pageQuestions = computed(() => questions.value.slice(pageStart.value, pageEnd.value));
const answeredCount = computed(() => Object.keys(answers).length);
const pageUnanswered = computed(() => pageQuestions.value.filter((q) => !answers[q.name]).length);

function pageAnsweredCount(page) {
	const start = page * PAGE_SIZE;
	const end = Math.min(start + PAGE_SIZE, questions.value.length);
	return questions.value.slice(start, end).filter((q) => answers[q.name]).length;
}

function goToPage(page) {
	unansweredHighlight.value = false;
	currentPage.value = page;
	window.scrollTo({ top: 0, behavior: "smooth" });
}

async function handleContinue() {
	submitError.value = null;
	if (pageUnanswered.value > 0) {
		unansweredHighlight.value = true;
		const first = pageQuestions.value.find((q) => !answers[q.name]);
		if (first) {
			await nextTick();
			document.getElementById(`q-${first.name}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
		}
		return;
	}
	goToPage(currentPage.value + 1);
}

// Load assessment on mount
const assessmentResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.icha_assessment.get_assessment",
	auto: true,
	onSuccess(data) {
		loading.value = false;
		if (data.already_attempted) {
			result.value = data;
		} else {
			questions.value = data.questions || [];
		}
	},
	onError(err) {
		loading.value = false;
		const msg = err?.exc_type || err?.message || "";
		if (msg.includes("PermissionError") || msg.includes("AuthenticationError")) {
			notEligibleReason.value = msg.includes("Research Assistant") ? "wrong_profession" : "permission_error";
		} else {
			submitError.value = __("Failed to load the assessment. Please refresh and try again.");
		}
	},
});

const notEligibleMessage = computed(() => {
	if (notEligibleReason.value === "wrong_profession") {
		return __("This assessment is only available to Research Assistants.");
	}
	return __("You are not eligible for this assessment.");
});

async function handleSubmit() {
	submitError.value = null;

	// Check all answered (across all pages)
	const unanswered = questions.value.filter((q) => !answers[q.name]);
	if (unanswered.length > 0) {
		unansweredHighlight.value = true;
		// Navigate to the page with the first unanswered question
		const firstIdx = questions.value.findIndex((q) => !answers[q.name]);
		const targetPage = Math.floor(firstIdx / PAGE_SIZE);
		if (targetPage !== currentPage.value) {
			goToPage(targetPage);
			await nextTick();
		}
		const first = unanswered[0];
		document.getElementById(`q-${first.name}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
		return;
	}

	submitting.value = true;
	try {
		const submitResource = createResource({
			url: "onerc_vmms.volunteer_and_member_management.api.icha_assessment.submit_assessment",
		});
		const res = await submitResource.submit({ answers: JSON.stringify({ ...answers }) });
		justSubmitted.value = true;
		result.value = res;
		window.scrollTo({ top: 0, behavior: "smooth" });
	} catch (err) {
		const msg = err?.exc_type || err?.message || "";
		if (msg.includes("already")) {
			submitError.value = __("You have already submitted this assessment.");
			assessmentResource.reload();
		} else {
			submitError.value = __("Submission failed. Please try again.");
		}
	} finally {
		submitting.value = false;
	}
}
</script>
