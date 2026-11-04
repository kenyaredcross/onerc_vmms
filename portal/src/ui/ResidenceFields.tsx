import { useEffect } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";
import { API } from "../lib/api";
import type { GeoLevel, GeoNode, PersonalDetails } from "../portal/types";
import { RegistrationGeoSelects } from "./RegistrationGeoSelects";
import { Field, FieldSet, SelectInput, TextArea, TextInput } from "./form";

export function ResidenceFields({
	residency,
	onResidency,
	sameHome,
	onSameHome,
	chain,
	onChain,
	country,
	onCountry,
	address,
	onAddress,
	details,
	onDetails,
	branchChain = [],
}: {
	residency: string;
	onResidency: (value: string) => void;
	sameHome: boolean;
	onSameHome: (value: boolean) => void;
	chain: GeoNode[];
	branchChain?: GeoNode[];
	onChain: (value: GeoNode[]) => void;
	country: string;
	onCountry: (value: string) => void;
	address: string;
	onAddress: (value: string) => void;
	recordedHome?: string | null;
	details: PersonalDetails;
	onDetails: (value: PersonalDetails) => void;
}) {
	const ladder = useFrappeGetCall<{ message: { levels: GeoLevel[] } }>(API.geoLadder, undefined, "geo:ladder");
	const hasCounty = ladder.data?.message?.levels.some((level) => level.name.toLowerCase() === "county");
	const addressChain = sameHome ? branchChain : chain;
	useEffect(() => {
		if (residency !== "Local") return;
		const next = { ...details };
		let changed = false;
		const county = addressChain.find((row) => row.level_name.toLowerCase() === "county");
		if (county && details.county && county.label !== details.county) {
			next.sub_county = "";
			next.ward = "";
			changed = true;
		}
		const subCounty = addressChain.find((row) => row.level_name.toLowerCase().replace(/[-_\s]/g, "") === "subcounty");
		if (subCounty && details.sub_county && subCounty.label !== details.sub_county) {
			next.ward = "";
			changed = true;
		}
		for (const [level, key] of [["county", "county"], ["subcounty", "sub_county"], ["ward", "ward"]] as const) {
			const node = addressChain.find((row) => row.level_name.toLowerCase().replace(/[-_\s]/g, "") === level);
			if (node && next[key] !== node.label) { next[key] = node.label; changed = true; }
		}
		if (changed) onDetails(next);
	}, [addressChain, residency, details, onDetails]);
	const fields = [
		["county", "County"],
		["sub_county", "Sub County"],
		["ward", "Ward"],
		["administrative_location", "Location"],
		["sub_location", "Sub Location"],
	] as const;
	return (
		<FieldSet
			title="Contact & Location"
		>
			<div className="space-y-4">
				<Field label="Residence" htmlFor="join-residency">
					<SelectInput
						id="join-residency"
						value={residency}
						options={["Local", "Abroad"]}
						onChange={onResidency}
					/>
				</Field>
				{residency === "Abroad" ? (
					<>
						<Field label="Country of residence" htmlFor="join-residence-country">
							<TextInput id="join-residence-country" value={country} onChange={onCountry} />
						</Field>
						<Field label="Address abroad" htmlFor="join-residence-address">
							<TextArea id="join-residence-address" value={address} onChange={onAddress} />
						</Field>
					</>
				) : (
					<>
						<label className="flex items-center gap-2 text-sm">
							<input
								type="checkbox"
								checked={sameHome}
								onChange={(event) => onSameHome(event.target.checked)}
							/>
							Same as Branch / County
						</label>
						<div id="join-home" className="grid gap-4 sm:grid-cols-2">
							{!sameHome && <RegistrationGeoSelects chain={chain} onChain={onChain} idPrefix="home" inline />}
							{fields.filter(([key]) => !hasCounty || !["county", "sub_county", "ward"].includes(key)).map(([key, label]) => (
								<Field key={key} label={label} htmlFor={`residence-${key}`}>
									<TextInput
										id={`residence-${key}`}
										value={details[key] ?? ""}
										onChange={(value) => onDetails({ ...details, [key]: value })}
									/>
								</Field>
							))}
						</div>
					</>
				)}
			</div>
		</FieldSet>
	);
}
