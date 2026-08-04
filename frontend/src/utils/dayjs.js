import dayjs from "dayjs/esm";
import relativeTime from "dayjs/esm/plugin/relativeTime";
import localizedFormat from "dayjs/esm/plugin/localizedFormat";
import updateLocale from "dayjs/esm/plugin/updateLocale";
import isToday from "dayjs/esm/plugin/isToday";
import isSameOrBefore from "dayjs/esm/plugin/isSameOrBefore";
import isSameOrAfter from "dayjs/esm/plugin/isSameOrAfter";
import utc from "dayjs/esm/plugin/utc";
import timezone from "dayjs/esm/plugin/timezone";

dayjs.extend(updateLocale);
dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);
dayjs.extend(isToday);
dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);
dayjs.extend(utc);
dayjs.extend(timezone);

export const DATE_FORMAT = "D MMM YYYY";
export const DATE_TIME_FORMAT = "D MMM YYYY, h:mm A";

export function formatDate(value, format = DATE_FORMAT) {
	if (!value) return "";
	const date = dayjs(value);
	return date.isValid() ? date.format(format) : "";
}

export function formatDateTime(value) {
	return formatDate(value, DATE_TIME_FORMAT);
}

export default dayjs;
