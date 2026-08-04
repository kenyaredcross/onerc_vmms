import { useId } from "vue";

export function useFieldErrors(getErrors, step) {
	const uid = useId();

	function errorId(label) {
		const slug = String(label)
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/^-+|-+$/g, "");
		return `${uid}-${slug}-error`;
	}

	function errorFor(label) {
		const message = getErrors()?.[step]?.[label];
		return typeof message === "string" ? message : null;
	}

	function fieldProps(label, describedBy) {
		const message = errorFor(label);
		const ids = [describedBy, message ? errorId(label) : null].filter(Boolean);

		return {
			"aria-invalid": message ? "true" : undefined,
			"aria-describedby": ids.length ? ids.join(" ") : undefined,
		};
	}

	return { errorId, errorFor, fieldProps };
}
