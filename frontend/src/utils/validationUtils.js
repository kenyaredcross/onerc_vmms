const isDateValid = (date) => date && !isNaN(new Date(date));
const isPastDate = (date) => new Date(date) < new Date();
const isEmailValid = (email) => {
	const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
	return emailRegex.test(email);
};
const isPhoneNumberValid = (phone) => {
	if (!phone) return true;
	const cleanPhone = phone.toString().replace(/\s+/g, "");

	const phoneRegex = /^(?:\+254|0)(7\d{8}|1\d{8})$/;
	return phoneRegex.test(cleanPhone);
};

const isRowEffectivelyEmpty = (row) => {
	if (!row || typeof row !== "object") return true;
	const keys = Object.keys(row);
	if (keys.length === 0) return true;

	return keys.every(
		(key) =>
			["name", "idx", "parent", "doctype"].includes(key) ||
			row[key] === null ||
			row[key] === undefined ||
			row[key] === "" ||
			(Array.isArray(row[key]) && row[key].length === 0) ||
			(typeof row[key] === "object" && Object.keys(row[key]).length === 0),
	);
};
const getFieldLabel = (field) => field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function validateForm(form, stepConfig) {
	const errors = [];
	form = form || {};

	const pushError = (msg) => msg && errors.push(msg);

	const formChecks = stepConfig.formChecks || {};

	runChecks(form, formChecks, pushError);

	const tables = stepConfig.tableChecks || {};

	for (const tableKey in tables) {
		const tableConfig = tables[tableKey];
		const rows = form[tableKey];

		if (!Array.isArray(rows) || rows.length === 0) continue;

		rows.forEach((row, index) => {
			const prefix = `${tableConfig.label || tableKey}: Row ${index + 1}`;

			if (isRowEffectivelyEmpty(row)) {
				pushError(`${prefix} appears to be empty.`);
				return;
			}

			runChecks(row, tableConfig, (msg) => pushError(`${prefix}, ${msg}`));
		});
	}

	return [...new Set(errors)];
}

function runChecks(data, rules, pushError) {
	if (Array.isArray(rules.requiredFields)) {
		rules.requiredFields.forEach((req) => {
			let field,
				condition = true;

			if (typeof req === "string") {
				field = req;
			} else {
				field = req.field;
				condition = req.condition ? req.condition(data) : true;
			}

			const value = data[field];
			if (condition && (!value || String(value).trim() === "")) {
				pushError(`"${getFieldLabel(field)}" is required.`);
			}
		});
	}

	if (Array.isArray(rules.emailChecks)) {
		rules.emailChecks.forEach((check) => {
			const value = data[check.field];
			if (value && !isEmailValid(value)) {
				pushError(`"${getFieldLabel(check.field)}" is not a valid email address.`);
			}
		});
	}

	if (Array.isArray(rules.phoneChecks)) {
		rules.phoneChecks.forEach((check) => {
			const value = data[check.field];

			if (value && !isPhoneNumberValid(value)) {
				pushError(`"${getFieldLabel(check.field)}" is not a valid phone number.`);
			}
		});
	}

	if (Array.isArray(rules.dateChecks)) {
		rules.dateChecks.forEach((check) => {
			const value = data[check.field];
			const condition = check.condition ? check.condition(data) : value;

			if (condition && value) {
				if (!isDateValid(value)) {
					pushError(`"${getFieldLabel(check.field)}" is not a valid date.`);
				} else if (
					typeof check.validation === "function" &&
					!check.validation(value, data)
				) {
					const msg =
						typeof check.error === "function" ? check.error(data) : check.error;

					pushError(`"${getFieldLabel(check.field)}" ${msg}`);
				}
			}
		});
	}

	if (Array.isArray(rules.customChecks)) {
		rules.customChecks.forEach((fn) => {
			try {
				const result = fn(data);
				if (Array.isArray(result)) result.forEach(pushError);
			} catch (err) {
				console.error("Validation error:", err);
			}
		});
	}
}

export { isDateValid, isEmailValid, isPastDate, isPhoneNumberValid, isRowEffectivelyEmpty };
