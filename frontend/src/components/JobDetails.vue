<template>
	<div v-if="job.data" class="min-h-screen">
		<div class="max-w-7xl mx-auto mb-4 md:px-4 lg:px-8 md:py-6">
			<div class="bg-surface-base rounded-2xl overflow-hidden border border-outline-gray-2">
				<!-- Hero Banner -->
				<div
					class="relative bg-gradient-to-r from-red-600 to-red-700 px-5 sm:px-8 py-8 sm:py-12 text-white"
				>
					<div
						class="absolute inset-0 opacity-10 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHoiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLW9wYWNpdHk9Ii4wNSIgc3Ryb2tlLXdpZHRoPSIyIi8+PC9nPjwvc3ZnPg==')]"
					></div>
					<div
						class="relative flex flex-col sm:flex-row items-start sm:items-center gap-5"
					>
						<!-- Logo -->
						<div class="shrink-0">
							<img
								v-if="job.data.company_logo"
								:src="job.data.company_logo"
								class="w-20 h-20 sm:w-24 sm:h-24 rounded-xl object-contain bg-surface-base p-3 shadow-lg cursor-pointer hover:scale-105 transition-transform duration-200"
								:alt="__('Company Logo')"
								@click="redirectToWebsite(job.data.website)"
							/>
							<div
								v-else
								class="w-20 h-20 sm:w-24 sm:h-24 flex items-center justify-center rounded-xl bg-surface-base text-red-600 font-black text-3xl shadow-lg select-none"
							>
								{{ getCompanyAbbr(job.data.company) }}
							</div>
						</div>

						<!-- Title + Tags -->
						<div class="flex-1 min-w-0">
							<h1
								class="text-3xl sm:text-5xl font-black leading-tight mb-3 text-white drop-shadow"
							>
								{{ __(job.data.job_title) }}
							</h1>
							<div class="flex flex-wrap gap-2">
								<span
									class="px-3 py-1 rounded-full bg-white/20 backdrop-blur-sm text-xs-semibold sm:text-sm border border-white/30"
								>
									{{ __(job.data.company) }}
								</span>
								<span
									v-if="job.data.department"
									class="px-3 py-1 rounded-full bg-white/20 backdrop-blur-sm text-xs-semibold sm:text-sm border border-white/30"
								>
									{{ __(job.data.department) }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Body -->
				<div class="px-4 sm:px-8 py-6 sm:py-10 space-y-10">
					<!-- Stats Grid -->
					<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
						<div
							class="group relative overflow-hidden bg-surface-gray-1 p-4 sm:p-5 rounded-xl border border-outline-gray-1 hover:border-outline-red-1 hover:shadow-md transition-all duration-200"
						>
							<CalendarDays class="w-5 h-5 text-ink-red-6 mb-2" />
							<p class="text-xs-bold text-ink-gray-4 uppercase tracking-wider mb-1">
								{{ __("Posted") }}
							</p>
							<p class="text-sm-semibold text-ink-gray-9">
								{{ __(dayjs(job.data.creation).fromNow()) }}
							</p>
						</div>

						<div
							class="group relative overflow-hidden bg-surface-red-1 p-4 sm:p-5 rounded-xl border border-outline-gray-1 hover:border-outline-red-1 hover:shadow-md transition-all duration-200"
						>
							<ClipboardType class="w-5 h-5 text-ink-red-6 mb-2" />
							<p class="text-xs-bold text-ink-gray-4 uppercase tracking-wider mb-1">
								{{ __("Type") }}
							</p>
							<p class="text-sm-semibold text-ink-gray-9">
								{{ __(job.data.employment_type) }}
							</p>
						</div>

						<div
							class="group relative overflow-hidden bg-surface-blue-1 p-4 sm:p-5 rounded-xl border border-outline-gray-1 hover:border-outline-blue-1 hover:shadow-md transition-all duration-200"
						>
							<Briefcase class="w-5 h-5 text-ink-blue-5 mb-2" />
							<p class="text-xs-bold text-ink-gray-4 uppercase tracking-wider mb-1">
								{{ __("Level") }}
							</p>
							<p class="text-sm-semibold text-ink-gray-9">
								{{
									__(
										job.data.designation?.designation_name ||
											job.data.designation?.name
									)
								}}
							</p>
						</div>

						<div
							v-if="job.data.minimum_years_of_experience"
							class="group relative overflow-hidden bg-surface-green-1 p-4 sm:p-5 rounded-xl border border-outline-gray-1 hover:border-outline-green-1 hover:shadow-md transition-all duration-200"
						>
							<Award class="w-5 h-5 text-ink-green-6 mb-2" />
							<p class="text-xs-bold text-ink-gray-4 uppercase tracking-wider mb-1">
								{{ __("Experience") }}
							</p>
							<p class="text-sm-semibold text-ink-gray-9">
								{{ __(job.data.minimum_years_of_experience) }}{{ __("+ Years") }}
							</p>
						</div>
					</div>

					<!-- Location Strip -->
					<div
						v-if="job.data.job_location || job.data.company"
						class="p-4 sm:p-6 bg-surface-gray-1 rounded-xl border border-outline-gray-1"
					>
						<div class="flex flex-wrap gap-6 sm:gap-10">
							<div v-if="job.data.company" class="flex items-center gap-3">
								<div
									class="w-9 h-9 rounded-full bg-surface-red-1 flex items-center justify-center shrink-0"
								>
									<svg
										class="w-4 h-4 text-ink-red-6"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
										/>
									</svg>
								</div>
								<div>
									<p class="text-xs-bold text-ink-gray-4 uppercase">
										{{ __("County") }}
									</p>
									<p class="text-sm-semibold text-ink-gray-9">
										{{ __(job.data.company) }}
									</p>
								</div>
							</div>

							<div v-if="job.data.job_location" class="flex items-center gap-3">
								<div
									class="w-9 h-9 rounded-full bg-surface-blue-1 flex items-center justify-center shrink-0"
								>
									<svg
										class="w-4 h-4 text-ink-blue-5"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
										/>
									</svg>
								</div>
								<div>
									<p class="text-xs-bold text-ink-gray-4 uppercase">
										{{ __("Location") }}
									</p>
									<p class="text-sm-semibold text-ink-gray-9">
										{{ __(job.data.job_location) }}
									</p>
								</div>
							</div>

							<div v-if="job.data.profession" class="flex items-center gap-3">
								<div
									class="w-9 h-9 rounded-full bg-surface-violet-1 flex items-center justify-center shrink-0"
								>
									<svg
										class="w-4 h-4 text-ink-gray-7"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
										/>
									</svg>
								</div>
								<div>
									<p class="text-xs-bold text-ink-gray-4 uppercase">
										{{ __("Profession") }}
									</p>
									<p class="text-sm-semibold text-ink-gray-9">
										{{ __(job.data.profession) }}
									</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Skills -->
					<section v-if="job.data.required_skills?.length">
						<div class="flex items-center gap-3 mb-4">
							<div
								class="w-10 h-10 rounded-xl bg-surface-red-4 flex items-center justify-center"
							>
								<CheckCircle class="w-5 h-5 text-white" />
							</div>
							<h2 class="text-2xl sm:text-3xl font-black text-ink-gray-9">
								{{ __("Core Skills Required") }}
							</h2>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
							<div
								v-for="(skill, idx) in job.data.required_skills"
								:key="idx"
								class="flex items-center gap-3 p-3 sm:p-4 bg-surface-base rounded-xl border border-outline-gray-1 hover:border-outline-red-1 hover:transition-all duration-200"
							>
								<div
									class="w-7 h-7 rounded-lg bg-surface-red-1 flex items-center justify-center shrink-0"
								>
									<Check class="w-3.5 h-3.5 text-ink-red-6" />
								</div>
								<span class="text-sm-medium text-ink-gray-8">{{
									__(skill?.skill)
								}}</span>
							</div>
						</div>
					</section>

					<!-- Qualifications -->
					<section v-if="hasQualification(job.data)">
						<div class="flex items-center gap-3 mb-4">
							<div
								class="w-10 h-10 rounded-xl bg-surface-blue-3 flex items-center justify-center"
							>
								<FileText class="w-5 h-5 text-white" />
							</div>
							<h2 class="text-2xl sm:text-3xl font-black text-ink-gray-9">
								{{ __("Qualifications") }}
							</h2>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
							<div
								class="p-4 sm:p-5 bg-surface-blue-1 rounded-xl border border-outline-gray-1"
							>
								<p
									class="text-xs font-black text-ink-blue-5 uppercase tracking-widest mb-1"
								>
									{{ __("Minimum Qualification") }}
								</p>
								<p class="text-base-bold text-ink-gray-9">
									{{ __(job.data.minimum_qualification_level) }}
								</p>
							</div>
							<div
								class="p-4 sm:p-5 bg-surface-gray-1 rounded-xl border border-outline-gray-1"
							>
								<p
									class="text-xs font-black text-ink-gray-5 uppercase tracking-widest mb-1"
								>
									{{ __("Field of Study") }}
								</p>
								<p class="text-base-bold text-ink-gray-9">
									{{ __(job.data.preferred_field_of_study) }}
								</p>
							</div>
							<div
								class="p-4 sm:p-5 bg-surface-green-1 rounded-xl border border-outline-gray-1"
							>
								<p
									class="text-xs font-black text-ink-green-6 uppercase tracking-widest mb-1"
								>
									{{ __("Minimum GPA / Grade") }}
								</p>
								<p class="text-base-bold text-ink-gray-9">
									{{ __(job.data.required_gpa__grade) }}
								</p>
							</div>
							<div
								class="p-4 sm:p-5 bg-surface-amber-1 rounded-xl border border-outline-gray-1"
							>
								<p
									class="text-xs font-black text-ink-amber-6 uppercase tracking-widest mb-1"
								>
									{{ __("Equivalent Experience") }}
								</p>
								<p class="text-base-bold text-ink-gray-9">
									{{ __(job.data.allow_equivalent_experience ? "Yes" : "No") }}
								</p>
							</div>
						</div>
					</section>

					<!-- Licences -->
					<section v-if="job.data.required_licences?.length">
						<div class="flex items-center gap-3 mb-4">
							<div
								class="w-10 h-10 rounded-xl bg-surface-green-3 flex items-center justify-center"
							>
								<Award class="w-5 h-5 text-white" />
							</div>
							<h2 class="text-2xl sm:text-3xl font-black text-ink-gray-9">
								{{ __("Required Licenses & Certifications") }}
							</h2>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
							<div
								v-for="(lic, idx) in job.data.required_licences"
								:key="idx"
								class="flex items-center gap-3 p-3 sm:p-4 bg-surface-base rounded-xl border border-outline-gray-1 hover:border-outline-green-1 hover:transition-all duration-200"
							>
								<div
									class="w-7 h-7 rounded-lg bg-surface-green-1 flex items-center justify-center shrink-0"
								>
									<Check class="w-3.5 h-3.5 text-ink-green-6" />
								</div>
								<span class="text-sm-medium text-ink-gray-8">{{
									__(lic?.license_type)
								}}</span>
							</div>
						</div>
					</section>

					<!-- Description -->
					<section v-if="job.data.description">
						<div class="flex items-center gap-3 mb-4">
							<div
								class="w-10 h-10 rounded-xl bg-surface-gray-8 flex items-center justify-center"
							>
								<FileText class="w-5 h-5 text-white" />
							</div>
							<h2 class="text-2xl sm:text-3xl font-black text-ink-gray-8">
								{{ __("Opportunity Description") }}
							</h2>
						</div>
						<div
							class="p-5 sm:p-8 bg-surface-gray-1 rounded-xl border border-outline-gray-1"
						>
							<div
								v-html="sanitizeRichHtml(__(job.data.description))"
								class="frappe-editor-content prose prose-sm sm:prose-base max-w-none"
							></div>
						</div>
					</section>

					<!-- Apply -->
					<div class="pt-6 border-t border-outline-gray-1">
						<NewJobApplication />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	Award,
	Briefcase,
	CalendarDays,
	Check,
	CheckCircle,
	ClipboardType,
	FileText,
} from "lucide-vue-next";
import { inject } from "vue";
import NewJobApplication from "../pages/NewJobApplication.vue";
import { sanitizeRichHtml } from "../utils/sanitizeHtml";

const props = defineProps({
	job: Object,
});

const dayjs = inject("$dayjs");

const redirectToWebsite = (url) => {
	if (url) window.open(url, "_blank");
};

const getCompanyAbbr = (name) =>
	name
		? name
				.split(" ")
				.map((word) => word[0])
				.join("")
				.slice(0, 2)
				.toUpperCase()
		: "NA";

const hasQualification = (job) =>
	job.minimum_qualification_level ||
	job.preferred_field_of_study ||
	job.required_gpa__grade ||
	job.allow_equivalent_experience;
</script>
<style scoped>
/* Override inline styles injected by Frappe's editor */
.frappe-editor-content :deep(*) {
	color: unset !important;
	background-color: unset !important;
}

.frappe-editor-content :deep(p),
.frappe-editor-content :deep(li),
.frappe-editor-content :deep(td),
.frappe-editor-content :deep(span) {
	color: var(--ink-gray-8) !important;
}

.frappe-editor-content :deep(h1),
.frappe-editor-content :deep(h2),
.frappe-editor-content :deep(h3),
.frappe-editor-content :deep(h4) {
	color: var(--ink-gray-9) !important;
	font-weight: 800;
}

.frappe-editor-content :deep(a) {
	color: var(--ink-red-6) !important;
}

.frappe-editor-content :deep(strong) {
	color: var(--ink-gray-9) !important;
	font-weight: 700;
}

.frappe-editor-content :deep(th) {
	background-color: var(--surface-gray-2) !important;
	font-weight: 700;
	padding: 0.75rem;
}

.frappe-editor-content :deep(td) {
	padding: 0.75rem;
}

.frappe-editor-content :deep(table) {
	width: 100%;
	border-collapse: collapse;
}

.frappe-editor-content :deep(td),
.frappe-editor-content :deep(th) {
	border: 1px solid var(--outline-gray-2) !important;
}
</style>
