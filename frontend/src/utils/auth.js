const APP_BASE = "/vmms";
const LOGIN_URL = "/login";

export function loginUrl(redirectTo) {
	if (!redirectTo) return LOGIN_URL;
	const target = redirectTo.startsWith(APP_BASE) ? redirectTo : `${APP_BASE}${redirectTo}`;
	return `${LOGIN_URL}?redirect-to=${encodeURIComponent(target)}`;
}

export function signupUrl() {
	return `${LOGIN_URL}#signup`;
}

export function goToLogin(redirectTo) {
	window.location.href = loginUrl(redirectTo);
}

export function goToSignup() {
	window.location.href = signupUrl();
}
