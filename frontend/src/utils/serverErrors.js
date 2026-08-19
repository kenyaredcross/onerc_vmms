/**
 * Turn a frappe-ui request error into a list of human-readable messages.
 *
 * frappe-ui puts the server's `_server_messages` on `err.messages`, while
 * `err.message` is only a technical string built from the request URL and the
 * exception class (e.g. "/api/method/…update_user_details ValidationError").
 * Reading `err.message` therefore hides whatever the server actually said.
 *
 * @param {Error & {messages?: string[]}} err
 * @param {string} fallback shown when the server sent no usable message
 * @returns {string[]}
 */
export function getServerErrorMessages(err, fallback) {
	const messages = (err?.messages || []).filter(Boolean);

	if (messages.length) {
		return messages;
	}

	return [err?.message || fallback];
}
