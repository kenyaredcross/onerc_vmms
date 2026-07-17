<template>
	<div v-if="job.data" class="min-h-screen">
		<div class="max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
			<div class="bg-white rounded-3xl shadow-xl overflow-hidden border border-gray-100">
				<div
					class="relative bg-gradient-to-r from-red-600 to-red-700 px-8 py-12 text-white"
				>
					<div
						class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHoiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLW9wYWNpdHk9Ii4wNSIgc3Ryb2tlLXdpZHRoPSIyIi8+PC9nPjwvc3ZnPg==')] opacity-20"
					></div>
					<div
						class="relative flex flex-col sm:flex-row items-start sm:items-center gap-6"
					>
						<div class="relative group">
							<div
								class="absolute inset-0 bg-white/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all"
							></div>
							<img
								v-if="job.data.company_logo"
								:src="job.data.company_logo"
								class="relative w-24 h-24 sm:w-28 sm:h-28 rounded-2xl object-contain bg-white p-4 shadow-2xl cursor-pointer hover:scale-105 transition-transform duration-300"
								:alt="__('Company Logo')"
								@click="redirectToWebsite(job.data.website)"
							/>
							<div
								v-else
								class="relative w-24 h-24 sm:w-28 sm:h-28 flex items-center justify-center rounded-2xl bg-white text-red-600 font-black text-3xl shadow-2xl select-none"
							>
								{{ __(getCompanyAbbr(job.data.company)) }}
							</div>
						</div>

						<div class="flex-1">
							<h1
								class="text-4xl sm:text-5xl font-black leading-tight mb-3 text-white drop-shadow-lg"
							>
								{{ __(job.data.job_title) }}
							</h1>
							<div class="flex flex-wrap gap-3">
								<span
									class="px-4 py-1.5 rounded-full bg-white/20 backdrop-blur-sm text-sm font-semibold border border-white/30"
								>
									{{ __(job.data.company) }}
								</span>
								<span
									v-if="job.data.department"
									class="px-4 py-1.5 rounded-full bg-white/20 backdrop-blur-sm text-sm font-semibold border border-white/30"
								>
									{{ __(job.data.department) }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<div class="px-8 py-10">
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-12">
						<div
							class="group relative overflow-hidden bg-gradient-to-br from-gray-50 to-white p-6 rounded-2xl border border-gray-200 hover:border-red-300 hover:shadow-lg transition-all duration-300"
						>
							<CalendarDays class="w-6 h-6 text-red-600 mb-3" />
							<p
								class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1"
							>
								{{ __("Posted") }}
							</p>
							<p class="text-sm font-semibold text-gray-900">
								{{ __(dayjs(job.data.creation).fromNow()) }}
							</p>
							<div
								class="absolute top-0 right-0 w-20 h-20 bg-red-100/50 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"
							></div>
						</div>

						<div
							class="group relative overflow-hidden bg-gradient-to-br from-red-50 to-white p-6 rounded-2xl border border-red-200 hover:border-red-400 hover:shadow-lg transition-all duration-300"
						>
							<ClipboardType class="w-6 h-6 text-red-600 mb-3" />
							<p
								class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1"
							>
								{{ __("Type") }}
							</p>
							<p class="text-sm font-semibold text-gray-900">
								{{ __(job.data.employment_type) }}
							</p>
							<div
								class="absolute top-0 right-0 w-20 h-20 bg-red-200/50 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"
							></div>
						</div>

						<div
							class="group relative overflow-hidden bg-gradient-to-br from-blue-50 to-white p-6 rounded-2xl border border-blue-200 hover:border-blue-400 hover:shadow-lg transition-all duration-300"
						>
							<Briefcase class="w-6 h-6 text-red-600 mb-3" />
							<p
								class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1"
							>
								{{ __("Level") }}
							</p>
							<p class="text-sm font-semibold text-gray-900">
								{{
									__(
										job.data.designation?.designation_name ||
											job.data.designation?.name
									)
								}}
							</p>
							<div
								class="absolute top-0 right-0 w-20 h-20 bg-blue-200/50 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"
							></div>
						</div>

						<div
							v-if="job.data.minimum_years_of_experience"
							class="group relative overflow-hidden bg-gradient-to-br from-green-50 to-white p-6 rounded-2xl border border-green-200 hover:border-green-400 hover:shadow-lg transition-all duration-300"
						>
							<Award class="w-6 h-6 text-red-600 mb-3" />
							<p
								class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1"
							>
								{{ __("Experience") }}
							</p>
							<p class="text-sm font-semibold text-gray-900">
								{{ __(job.data.minimum_years_of_experience) }}{{ __("+ Years") }}
							</p>
							<div
								class="absolute top-0 right-0 w-20 h-20 bg-green-200/50 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-500"
							></div>
						</div>
					</div>

					<div
						v-if="job.data.job_location || job.data.company"
						class="mb-12 p-6 bg-gradient-to-r from-gray-50 to-red-50/30 rounded-2xl border border-gray-200"
					>
						<div class="flex flex-wrap gap-8">
							<div v-if="job.data.company" class="flex items-center gap-3">
								<div
									class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center"
								>
									<svg
										class="w-5 h-5 text-red-600"
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
									<p class="text-xs font-bold text-gray-500 uppercase">
										{{ __("County") }}
									</p>
									<p class="text-base font-semibold text-gray-900">
										{{ __(job.data.company) }}
									</p>
								</div>
							</div>
							<div v-if="job.data.job_location" class="flex items-center gap-3">
								<div
									class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center"
								>
									<svg
										class="w-5 h-5 text-blue-600"
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
									<p class="text-xs font-bold text-gray-500 uppercase">
										{{ __("Location") }}
									</p>
									<p class="text-base font-semibold text-gray-900">
										{{ __(job.data.job_location) }}
									</p>
								</div>
							</div>
							<div v-if="job.data.profession" class="flex items-center gap-3">
								<div
									class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center"
								>
									<svg
										class="w-5 h-5 text-purple-600"
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
									<p class="text-xs font-bold text-gray-500 uppercase">
										{{ __("Profession") }}
									</p>
									<p class="text-base font-semibold text-gray-900">
										{{ __(job.data.profession) }}
									</p>
								</div>
							</div>
						</div>
					</div>

					<section v-if="job.data.required_skills?.length" class="mb-12">
						<div class="flex items-center gap-3 mb-6">
							<div
								class="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg"
							>
								<CheckCircle class="w-6 h-6 text-white" />
							</div>
							<h2 class="text-2xl font-black text-gray-900">
								{{ __("Core Skills Required") }}
							</h2>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
							<div
								v-for="(skill, idx) in job.data.required_skills"
								:key="idx"
								class="group flex items-center gap-3 p-4 bg-white rounded-xl border-2 border-gray-200 hover:border-red-400 hover:shadow-md transition-all duration-300"
							>
								<div
									class="w-8 h-8 rounded-lg bg-red-50 group-hover:bg-red-100 flex items-center justify-center transition-colors"
								>
									<Check class="w-4 h-4 text-red-600 font-bold" />
								</div>
								<span class="text-sm font-semibold text-gray-900">{{
									__(skill?.skill)
								}}</span>
							</div>
						</div>
					</section>

					<section v-if="hasQualification(job.data)" class="mb-12">
						<div class="flex items-center gap-3 mb-6">
							<div
								class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg"
							>
								<FileText class="w-6 h-6 text-white" />
							</div>
							<h2 class="text-2xl font-black text-gray-900">
								{{ __("Qualifications") }}
							</h2>
						</div>
						<div class="grid sm:grid-cols-2 gap-6">
							<div
								class="group p-6 bg-gradient-to-br from-white to-blue-50/50 rounded-2xl border-2 border-blue-200 hover:border-blue-400 hover:shadow-lg transition-all duration-300"
							>
								<p
									class="text-xs font-black text-blue-600 uppercase tracking-widest mb-2"
								>
									{{ __("Minimum Qualification") }}
								</p>
								<p class="text-lg font-bold text-gray-900">
									{{ __(job.data.minimum_qualification_level) }}
								</p>
							</div>
							<div
								class="group p-6 bg-gradient-to-br from-white to-purple-50/50 rounded-2xl border-2 border-purple-200 hover:border-purple-400 hover:shadow-lg transition-all duration-300"
							>
								<p
									class="text-xs font-black text-purple-600 uppercase tracking-widest mb-2"
								>
									{{ __("Field of Study") }}
								</p>
								<p class="text-lg font-bold text-gray-900">
									{{ __(job.data.preferred_field_of_study) }}
								</p>
							</div>
							<div
								class="group p-6 bg-gradient-to-br from-white to-green-50/50 rounded-2xl border-2 border-green-200 hover:border-green-400 hover:shadow-lg transition-all duration-300"
							>
								<p
									class="text-xs font-black text-green-600 uppercase tracking-widest mb-2"
								>
									{{ __("Minimum GPA / Grade") }}
								</p>
								<p class="text-lg font-bold text-gray-900">
									{{ __(job.data.required_gpa__grade) }}
								</p>
							</div>
							<div
								class="group p-6 bg-gradient-to-br from-white to-amber-50/50 rounded-2xl border-2 border-amber-200 hover:border-amber-400 hover:shadow-lg transition-all duration-300"
							>
								<p
									class="text-xs font-black text-amber-600 uppercase tracking-widest mb-2"
								>
									{{ __("Equivalent Experience") }}
								</p>
								<p class="text-lg font-bold text-gray-900">
									{{ __(job.data.allow_equivalent_experience ? "Yes" : "No") }}
								</p>
							</div>
						</div>
					</section>

					<section v-if="job.data.required_licences?.length" class="mb-12">
						<div class="flex items-center gap-3 mb-6">
							<div
								class="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center shadow-lg"
							>
								<Award class="w-6 h-6 text-white" />
							</div>
							<h2 class="text-2xl font-black text-gray-900">
								{{ __("Required Licenses & Certifications") }}
							</h2>
						</div>
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
							<div
								v-for="(lic, idx) in job.data.required_licences"
								:key="idx"
								class="group flex items-center gap-3 p-4 bg-white rounded-xl border-2 border-gray-200 hover:border-green-400 hover:shadow-md transition-all duration-300"
							>
								<div
									class="w-8 h-8 rounded-lg bg-green-50 group-hover:bg-green-100 flex items-center justify-center transition-colors"
								>
									<Check class="w-4 h-4 text-green-600 font-bold" />
								</div>
								<span class="text-sm font-semibold text-gray-900">{{
									__(lic?.license_type)
								}}</span>
							</div>
						</div>
					</section>

					<section v-if="job.data.description" class="mb-12">
						<div class="flex items-center gap-3 mb-6">
							<div
								class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center shadow-lg"
							>
								<FileText class="w-6 h-6 text-white" />
							</div>
							<h2 class="text-2xl font-black text-gray-900">
								{{ __("Opportunity Description") }}
							</h2>
						</div>
						<div
							class="p-8 bg-gradient-to-br from-white to-gray-50 rounded-2xl border-2 border-gray-200"
						>
							<div
								v-html="sanitizeRichHtml(__(job.data.description))"
								class="frappe-editor-content prose prose-sm sm:prose-base max-w-none"
							></div>
						</div>
					</section>

					<div class="pt-8 border-t-2 border-gray-200">
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
