const isDateValid = (date) => date && !isNaN(new Date(date));
const isPastDate = (date) => new Date(date) < new Date();
const isEmailValid = (email) => {
	const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
	return emailRegex.test(email);
};
const isPhoneNumberValid = (phone) => {
	const phoneRegex = /^\+?[\d\s-()]{7,20}$/;
	return phoneRegex.test(phone.toString().replace(/\s+/g, ""));
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

/**
 * Validates form data against a configuration array.
 *
 * @param {Object} form - The reactive form object containing child tables (arrays).
 * @param {Array<Object>} config - Configuration array for tables to check.
 * @returns {Array<string>} An array of error messages.
 */
export function validateForm(form, config) {
	const errors = [];

	for (const table of config) {
		const rows = form[table.field];
		if (!rows || rows.length === 0) continue;

		rows.forEach((row, index) => {
			const rowPrefix = `${table.label}: Row ${index + 1}`;

			if (isRowEffectivelyEmpty(row)) {
				errors.push(
					`${rowPrefix} appears to be empty. Please either complete it or remove it.`,
				);
				return;
			}

			table.requiredFields.forEach((req) => {
				let field,
					shouldCheck = true;

				if (typeof req === "string") {
					field = req;
				} else if (req && typeof req === "object") {
					field = req.field;
					shouldCheck = typeof req.condition === "function" ? req.condition(row) : true;
				}

				if (shouldCheck && (!row[field] || row[field] === "" || row[field] == null)) {
					errors.push(`${rowPrefix} is missing "${getFieldLabel(field)}".`);
				}
			});

			if (table.dateChecks) {
				table.dateChecks.forEach((check) => {
					const field = check.field;
					const date = row[field];

					const condition = check.condition ? check.condition(row) : date;

					if (condition && date) {
						if (!isDateValid(date)) {
							errors.push(
								`${rowPrefix}, "${getFieldLabel(field)}" is not a valid date.`,
							);
						} else if (
							typeof check.validation === "function" &&
							!check.validation(date, row)
						) {
							const errorMsg =
								typeof check.error === "function" ? check.error(row) : check.error;
							errors.push(`${rowPrefix}, "${getFieldLabel(field)}" ${errorMsg}`);
						}
					}
				});
			}

			if (table.emailChecks) {
				table.emailChecks.forEach((check) => {
					const field = check.field;
					const email = row[field];
					if (email && !isEmailValid(email)) {
						errors.push(`${rowPrefix}, "${getFieldLabel(field)}" ${check.error}`);
					}
				});
			}

			if (table.phoneChecks) {
				table.phoneChecks.forEach((check) => {
					const field = check.field;
					const phone = row[field];
					if (phone && !isPhoneNumberValid(phone)) {
						errors.push(`${rowPrefix}, "${getFieldLabel(field)}" ${check.error}`);
					}
				});
			}
		});
	}

	return errors;
}

export { isDateValid, isEmailValid, isPastDate, isPhoneNumberValid, isRowEffectivelyEmpty };
