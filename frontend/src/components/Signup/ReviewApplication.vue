<template>
	<div class="space-y-8">
		<h2 class="text-2xl font-bold text-red-700">
			{{ __("Review Your Application") }}
		</h2>

		<CollapsibleSection :title="__('Personal & Location Info')">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				<ReviewField label="Branch / County" :value="form.company" />
				<ReviewField label="Phone Number" :value="form.phone_number" />
				<ReviewField label="Email Address" :value="form.email_id" />
				<ReviewField label="Date of Birth" :value="form.date_of_birth" />
				<ReviewField label="Gender" :value="form.gender" />
				<ReviewField label="Marital Status" :value="form.marital_status" />
				<ReviewField label="Number of Dependants" :value="form.number_of_dependants" />
				<ReviewField
					label="Mobile Money (M-Pesa) Phone"
					:value="form.mpesa_mobile_phone"
				/>
				<ReviewField label="Blood Group" :value="form.blood_group" />
				<ReviewField label="KRCS Insurance" :value="form.has_insurance" />

				<ReviewField label="Ward" :value="form.ward" />
				<ReviewField label="Sub County" :value="form.sub_county" />
				<ReviewField label="Location" :value="form.administrative_location" />
				<ReviewField label="Sub Location" :value="form.sub_location" />
				<ReviewField label="County of Residence" :value="form.county" />

				<ReviewField label="Citizenship" :value="form.citizenship" />
				<ReviewField
					label="Identification Document Type"
					:value="form.identification_type"
				/>
				<ReviewField label="Identification Number" :value="form.id_number" />
				<ReviewField label="Country of Citizenship" :value="form.country_of_citizenship" />

				<ReviewField
					label="Consent to Use of Bio Data"
					:value="form.consent_to_use_of_bio_data ? 'Yes' : 'No'"
				/>
			</div>
		</CollapsibleSection>

		<CollapsibleSection :title="__('Additional Information')">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				<ReviewField label="Access to Internet" :value="form.access_to_internet" />
				<ReviewField label="Profession" :value="form.profession" />
				<ReviewField label="Reason for Joining" :value="form.reason_to_join_krcs" />

				<MultiSelect
					v-model="form.languages"
					doctype="Volunteer Language"
					:label="__('Languages')"
					:disabled="true"
					:readOnly="true"
				/>
				<MultiSelect
					v-model="form.driving_licence"
					doctype="Driving Licences"
					:label="__('Driving Licence')"
					:disabled="true"
					:readOnly="true"
				/>

				<div class="w-full md:col-span-3 space-y-6">
					<ChildTable
						v-model="form.disabilities"
						doctype="Employee Disability"
						label="Disabilities"
						:autoEditGrid="false"
						:readOnly="true"
					/>
					<ChildTable
						v-model="form.allergies"
						doctype="Allergy Table"
						label="Allergies"
						:autoEditGrid="false"
						:readOnly="true"
					/>
					<ChildTable
						v-model="form.education"
						doctype="Employee Education"
						label="Education"
						:autoEditGrid="false"
						:readOnly="true"
					/>
					<ChildTable
						v-model="form.courses"
						doctype="User External Course"
						label="Trainings & Certifications"
						:autoEditGrid="false"
						:readOnly="true"
					/>
					<ChildTable
						v-model="form.additional_skills"
						doctype="Additional Skill"
						label="Additional Skills"
						:autoEditGrid="false"
						:readOnly="true"
					/>
					<ChildTable
						v-model="form.licences"
						doctype="Personnel Licence"
						label="Licences"
						:autoEditGrid="false"
						:readOnly="true"
					/>
				</div>
			</div>
		</CollapsibleSection>

		<CollapsibleSection :title="__('Documents')">
			<ChildTable
				v-model="form.supporting_documents"
				doctype="Supporting Document"
				label="Supporting Documents"
				:autoEditGrid="false"
				:readOnly="true"
			/>
		</CollapsibleSection>
	</div>
</template>

<script setup>
import CollapsibleSection from "@/components/CollapsibleSection.vue";
import ChildTable from "@/components/Controls/ChildTable.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import ReviewField from "./ReviewField.vue";

const props = defineProps({
	form: { type: Object, required: true },
});
</script>
