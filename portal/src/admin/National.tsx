import { EditableText } from "../content/Editable";
import { AreaView } from "./oversight/AreaView";

/**
 * The whole country, region by region, for national staff.
 *
 * Opened by anybody assigned at the top of the society's tree, and by System
 * Manager. The same page as the region tab a level up: the table compares
 * regions, and choosing one narrows the breakdowns to it.
 */
export default function National() {
	return <AreaView mode="national" title={<EditableText k="admin.nav.national" fallback="National" />} />;
}
