import { EditableText } from "../content/Editable";
import { FaqBody } from "../guest/Faq";
import { PageHead } from "./ui/kit";

/**
 * The society's answers, inside the portal.
 *
 * **The same body as the public page, deliberately.** `FaqBody` is imported from
 * `guest/Faq` rather than reimplemented here, so a society that publishes an
 * answer publishes it once and a volunteer and a stranger read the same words.
 * Only the chrome differs: the public page carries the site header, this one
 * sits inside the portal shell and takes the portal's page head.
 *
 * **The content is core's.** `FAQ` and `FAQ Category` belong to onerc_core, and
 * this app stores no copy of either — see `api/faq.py`.
 */
export default function Help() {
	return (
		<>
			<PageHead
				eyebrow={<EditableText k="portal.help.eyebrow" fallback="Help" />}
				title={<EditableText k="portal.help.heading" fallback="Questions and answers" />}
				lead={
					<EditableText
						k="portal.help.lead"
						fallback="What people ask most often. If your question is not here, your branch would rather be asked twice than not at all."
					/>
				}
			/>

			{/* The heading is the page head above, so the body draws none of its
			    own — two titles on one screen is the same sentence twice. */}
			<FaqBody heading={false} />
		</>
	);
}
