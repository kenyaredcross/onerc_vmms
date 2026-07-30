<template>
	<section>
		<h2 class="text-xl font-bold text-red-700 mb-4">
			{{ __("Documents ") }}
		</h2>
		<!-- <div class="grid grid-cols-1 gap-6">
      <div class="space-y-2">
        <span class="text-gray-700"> Profile Photo </span>
        <Uploader
          label="Upload Profile Photo"
          :fileTypes="['.jpg', '.png']"
          :onSuccess="(f) => (localModel.profile_photo = f)"
        />
      </div>
    </div> -->

		<div
			v-if="requiredTypes.length"
			class="p-4 bg-amber-50 border border-amber-200 rounded-lg"
		>
			<p class="text-sm font-semibold text-amber-900 mb-2">
				{{ __("The following documents are required") }}
			</p>
			<ul class="space-y-1">
				<li
					v-for="type in requiredTypes"
					:key="type"
					class="flex items-center gap-2 text-sm"
					:class="missingTypes.includes(type) ? 'text-amber-800' : 'text-green-700'"
				>
					<component
						:is="missingTypes.includes(type) ? AlertCircle : CheckCircle2"
						class="w-4 h-4 flex-shrink-0"
					/>
					<span>{{ __(type) }}</span>
					<span v-if="missingTypes.includes(type)" class="text-xs">
						{{ __("— not attached yet") }}
					</span>
				</li>
			</ul>
		</div>

		<div class="mt-6">
			<ChildTable
				v-model="localModel.supporting_documents"
				doctype="Supporting Document"
				:autoEditGrid="true"
				label="Supporting Documents"
				@validationErrors="onChildErrors('supporting_documents', $event)"
			/>
		</div>
	</section>
</template>

<script setup>
import { AlertCircle, CheckCircle2 } from "lucide-vue-next";
import { computed } from "vue";
import ChildTable from "../Controls/ChildTable.vue";

const STEP_INDEX = 2;

const props = defineProps({
	modelValue: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
	requiredTypes: { type: Array, default: () => [] },
});

const missingTypes = computed(() => {
	const attached = new Set(
		(props.modelValue?.supporting_documents || [])
			.filter((row) => row?.type && row?.attachment)
			.map((row) => row.type)
	);

	return props.requiredTypes.filter((type) => !attached.has(type));
});

const emit = defineEmits(["update:modelValue", "update:errors"]);

const localModel = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

function onChildErrors(tableName, errMap) {
	const tableErrors = Object.fromEntries(errMap);
	const newErrors = { ...props.errors };

	const stepErrors = { ...(newErrors[STEP_INDEX] || {}) };

	if (Object.keys(tableErrors).length > 0) {
		stepErrors[tableName] = tableErrors;
	} else {
		delete stepErrors[tableName];
	}

	if (Object.keys(stepErrors).length > 0) {
		newErrors[STEP_INDEX] = stepErrors;
	} else {
		delete newErrors[STEP_INDEX];
	}

	emit("update:errors", newErrors);
}
</script>
