import { EditableText } from "../content/Editable";
import { AreaView } from "./oversight/AreaView";

/**
 * A region county by county, for whoever is responsible for it.
 *
 * Opened by somebody holding the society's regional oversight role at a region
 * (Kenya's Heads of Region), and by national staff, who may switch to any.
 * Everything on it is read-only; deciding a membership happens on the review
 * queue, which the page links to when something is waiting.
 */
export default function Region() {
	return <AreaView mode="region" title={<EditableText k="admin.nav.region" fallback="My region" />} />;
}
