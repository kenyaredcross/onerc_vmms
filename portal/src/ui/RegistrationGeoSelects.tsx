import { useEffect, useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";
import { API, errorMessage } from "../lib/api";
import type { GeoLevel, GeoNode } from "../portal/types";
import { Field } from "./form";
import { ErrorNote } from "./primitives";
import { GeoSelects } from "./GeoSelects";

type Props = {
	chain: GeoNode[];
	onChain: (chain: GeoNode[]) => void;
	allowedLevels?: string[];
	idPrefix?: string;
	inline?: boolean;
	/**
	 * Ask nothing below the deepest allowed level. Off by default: the join
	 * form reads sub-county and ward off this picker for the residence, even
	 * where placement stops at the county. The one-page membership asks no
	 * residence, so it stops.
	 */
	stopAtAllowed?: boolean;
};

/** Registration starts at County when the configured hierarchy has that level. */
export function RegistrationGeoSelects(props: Props) {
	const ladder = useFrappeGetCall<{ message: { levels: GeoLevel[] } }>(API.geoLadder, undefined, "geo:ladder");
	const levels = ladder.data?.message?.levels ?? [];
	const county = levels.find((level) => level.name.toLowerCase() === "county");
	// With `stopAtAllowed`, nothing below the county is asked for when nothing
	// below it can be recorded: a membership kept per county stops there.
	const deepestAllowed = Math.max(
		-Infinity,
		...levels.filter((level) => props.allowedLevels?.includes(level.key)).map((level) => level.order),
	);
	const countyIsLast = Boolean(
		props.stopAtAllowed && county && props.allowedLevels?.length && county.order >= deepestAllowed,
	);
	return county ? <CountySelects {...props} county={county} countyIsLast={countyIsLast} countyRung={[...new Set(levels.map((level) => level.order))].sort((a, b) => a - b).indexOf(county.order)} /> : <GeoSelects {...props} showSummary={!props.inline} />;
}

function CountySelects({ chain, onChain, allowedLevels, idPrefix = "geo", county, countyRung, countyIsLast = false, inline = false }: Props & { county: GeoLevel; countyRung: number; countyIsLast?: boolean }) {
	const [requested, setRequested] = useState<string | null>(null);
	const countyIndex = chain.findIndex((node) => node.level === county.key);
	const selected = countyIndex >= 0 ? chain[countyIndex] : null;
	const counties = useFrappeGetCall<{ message: { nodes: GeoNode[] } }>(
		API.geoBrowse, { level: county.key }, `geo:level:${county.key}`,
	);
	const ancestry = useFrappeGetCall<{ message: { node: string; chain: GeoNode[] } }>(
		API.geoChain, { node: requested ?? "" }, requested ? `geo:registration-path:${requested}` : null,
	);
	useEffect(() => {
		const result = ancestry.data?.message;
		if (requested && result?.node === requested && result.chain.some((node) => node.name === requested && node.level === county.key)) {
			onChain(result.chain);
			setRequested(null);
		}
	}, [requested, ancestry.data, county.key, onChain]);
	const error = counties.error || ancestry.error;
	return <div className={inline ? "contents" : "space-y-4"}>
		<Field label={county.name} htmlFor={`${idPrefix}-county`} required>
			<select id={`${idPrefix}-county`} value={requested ?? selected?.name ?? ""}
				disabled={counties.isLoading || Boolean(counties.error)}
				className="w-full rounded-xl border border-card-line bg-white px-3.5 py-2.5 text-sm focus:border-blue"
				onChange={(event) => { onChain([]); setRequested(event.target.value || null); }}>
				<option value="">{counties.isLoading ? "Loading…" : "Select county"}</option>
				{(counties.data?.message?.nodes ?? []).map((node) => <option key={node.name} value={node.name}>{node.label}</option>)}
			</select>
		</Field>
		{error && <ErrorNote>{errorMessage(error, "Unable to load counties.")}</ErrorNote>}
		{(selected || inline) && !countyIsLast && <GeoSelects chain={chain} onChain={onChain} allowedLevels={allowedLevels} idPrefix={idPrefix} fromIndex={(countyIndex >= 0 ? countyIndex : countyRung) + 1} showEmptyLevels inline={inline} showSummary={!inline} />}
	</div>;
}
