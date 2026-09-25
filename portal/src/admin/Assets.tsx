import { useContext, useEffect, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Button, Card, Empty, ErrorNote, PageHeading, Spinner } from "../ui/primitives";

type Branch = { name: string };
type Asset = { name: string; asset_name: string; category: string; unit: string; geo_node: string; total_quantity: number; available_quantity: number; is_active: number };
type Issue = { name: string; asset_name: string; volunteer_name: string; quantity: number; outstanding: number; geo_node: string; last_reminded_at?: string };
type Volunteer = { name: string; full_name: string; home_geo_node: string };
type ActionResult = { message?: { notification_queued?: boolean } };

function useDebounced(value: string) {
	const [settled, setSettled] = useState(value);
	useEffect(() => {
		const timer = window.setTimeout(() => setSettled(value.trim()), 250);
		return () => window.clearTimeout(timer);
	}, [value]);
	return settled;
}

const INPUT = "w-full rounded-lg border border-card-line bg-white px-3 py-2 text-sm";

export default function Assets() {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [branch, setBranch] = useState("");
	const [stockSearch, setStockSearch] = useState("");
	const [assetSearch, setAssetSearch] = useState("");
	const [volunteerSearch, setVolunteerSearch] = useState("");
	const [issueSearch, setIssueSearch] = useState("");
	const [asset, setAsset] = useState<Asset | null>(null);
	const [volunteer, setVolunteer] = useState<Volunteer | null>(null);
	const [quantity, setQuantity] = useState("1");
	const [returnAmounts, setReturnAmounts] = useState<Record<string, string>>({});
	const [name, setName] = useState("");
	const [category, setCategory] = useState("");
	const [unit, setUnit] = useState("each");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState("");
	const [notice, setNotice] = useState("");
	const stockTerm = useDebounced(stockSearch);
	const assetTerm = useDebounced(assetSearch);
	const volunteerTerm = useDebounced(volunteerSearch);
	const issueTerm = useDebounced(issueSearch);

	const branches = useFrappeGetCall<{ message: Branch[] }>(API.assetBranches, undefined, "asset-branches");
	const stock = useFrappeGetCall<{ message: { assets: Asset[]; has_more: boolean } }>(
		API.assetStock, { geo_node: branch || undefined, search: stockTerm || undefined }, `asset-stock:${branch}:${stockTerm}`,
	);
	const holdings = useFrappeGetCall<{ message: Issue[] }>(
		API.assetOutstanding, { geo_node: branch || undefined, search: issueTerm || undefined }, `asset-outstanding:${branch}:${issueTerm}`,
	);
	const assets = useFrappeGetCall<{ message: Asset[] }>(
		API.assetSearch, { geo_node: branch, search: assetTerm },
		branch && assetTerm.length >= 2 && !asset ? `asset-picker:${branch}:${assetTerm}` : null,
	);
	const people = useFrappeGetCall<{ message: Volunteer[] }>(
		API.assetSearchVolunteers, { geo_node: branch, search: volunteerTerm },
		branch && volunteerTerm.length >= 2 && !volunteer ? `asset-people:${branch}:${volunteerTerm}` : null,
	);
	const rows = stock.data?.message.assets ?? [];
	const issues = holdings.data?.message ?? [];
	const validQuantity = Number.isInteger(Number(quantity)) && Number(quantity) > 0;

	async function act(method: string, args: Record<string, string | number>, kind: "create" | "receive" | "issue" | "return" | "remind") {
		setBusy(true);
		setFailure("");
		setNotice("");
		try {
			const response = await call.post(method, args) as ActionResult;
			await Promise.all([stock.mutate(), holdings.mutate(), assets.mutate()]);
			if (kind === "create") { setName(""); setNotice("Asset added."); }
			if (kind === "receive") { setAsset(null); setAssetSearch(""); setNotice("Stock received."); }
			if (kind === "issue") {
				setAsset(null); setVolunteer(null); setAssetSearch(""); setVolunteerSearch("");
				setNotice(response?.message?.notification_queued
					? "Issue recorded. An in-app notification was queued for the volunteer."
					: "Issue recorded. This volunteer has no linked login, so no in-app notification was queued.");
			}
			if (kind === "return") { setReturnAmounts({}); setNotice("Return recorded."); }
			if (kind === "remind") setNotice(response?.message?.notification_queued
				? "Reminder queued for the volunteer."
				: "No reminder was queued because this volunteer has no linked login.");
			setQuantity("1");
		} catch (error) { setFailure(errorMessage(error)); }
		finally { setBusy(false); }
	}

	return <div className="space-y-6">
		<PageHeading title="Branch assets" lead="Find stock and volunteers by name, then record issues, returns and reminders." />
		{failure && <ErrorNote>{failure}</ErrorNote>}
		{notice && <p role="status" className="rounded-lg border border-blue/20 bg-blue/5 px-4 py-3 text-sm text-ink">{notice}</p>}
		<Card className="space-y-4 p-5">
			{branches.error && <ErrorNote>{errorMessage(branches.error)}</ErrorNote>}
			<label className="block text-sm font-semibold">Branch
				<select className={`${INPUT} mt-2`} value={branch} onChange={(event) => {
					setBranch(event.target.value); setAsset(null); setVolunteer(null); setAssetSearch(""); setVolunteerSearch("");
				}}>
					<option value="">All assigned branches</option>
					{(branches.data?.message ?? []).map((row) => <option key={row.name} value={row.name}>{row.name}</option>)}
				</select>
			</label>
			{branch && <div className="flex flex-wrap gap-2">
				<input className={`${INPUT} sm:w-56`} aria-label="New asset name" placeholder="New asset, e.g. helmet" value={name} onChange={(event) => setName(event.target.value)} />
				<input className={`${INPUT} sm:w-44`} aria-label="Category" placeholder="Category, e.g. PPE" value={category} onChange={(event) => setCategory(event.target.value)} />
				<input className={`${INPUT} sm:w-24`} aria-label="Unit" value={unit} onChange={(event) => setUnit(event.target.value)} />
				<Button disabled={busy || !name.trim()} onClick={() => act(API.assetCreate, { asset_name: name, geo_node: branch, category, unit }, "create")}>Add asset</Button>
			</div>}
		</Card>

		<Card className="space-y-4 p-5">
			{stock.error && <ErrorNote>{errorMessage(stock.error)}</ErrorNote>}
			<div className="flex flex-wrap items-end justify-between gap-3">
				<h2 className="text-lg font-semibold">Stock</h2>
				<input className={`${INPUT} sm:w-72`} type="search" aria-label="Search stock" placeholder="Search asset name" value={stockSearch} onChange={(event) => setStockSearch(event.target.value)} />
			</div>
			{stock.isLoading ? <Spinner label="Loading branch stock…" /> : rows.length === 0 ? <Empty title="No matching assets">Choose a branch and add stock, or change your search.</Empty> : <div className="overflow-x-auto">
				<table className="w-full text-left text-sm"><thead><tr><th>Asset</th><th>Branch</th><th>Total</th><th>Available</th><th>Issued</th><th></th></tr></thead><tbody>
					{rows.map((row) => <tr key={row.name} className="border-t"><td className="py-3 font-semibold">{row.asset_name}<span className="block font-normal text-muted">{row.category || row.unit}</span></td><td>{row.geo_node}</td><td>{row.total_quantity}</td><td>{row.available_quantity}</td><td>{row.total_quantity - row.available_quantity}</td><td>{branch === row.geo_node && <Button variant="soft" onClick={() => setAsset(row)}>Select</Button>}</td></tr>)}
				</tbody></table>
			</div>}
			{stock.data?.message.has_more && <p className="text-sm text-muted">Showing the first 50 matches. Search by asset name to narrow the list.</p>}
		</Card>

		{branch && <Card className="space-y-5 p-5">
			<h2 className="text-lg font-semibold">Receive or issue stock</h2>
			<div className="grid gap-4 md:grid-cols-2">
				<div>
					<label className="block text-sm font-semibold">Asset</label>
					{asset ? <div className="mt-2 flex items-center justify-between gap-2 rounded-lg border p-3 text-sm"><span><strong>{asset.asset_name}</strong> · {asset.available_quantity} available</span><button type="button" className="font-semibold text-blue" onClick={() => setAsset(null)}>Change</button></div> : <>
						<input className={`${INPUT} mt-2`} type="search" placeholder="Search asset name or category" value={assetSearch} onChange={(event) => setAssetSearch(event.target.value)} />
						{assets.error && <ErrorNote>{errorMessage(assets.error)}</ErrorNote>}
						{assetTerm.length >= 2 && assetSearch.trim() === assetTerm && <SearchResults loading={assets.isLoading} empty="No matching assets in this branch" full={(assets.data?.message.length ?? 0) === 20} rows={(assets.data?.message ?? []).map((row) => ({ id: row.name, title: row.asset_name, detail: `${row.available_quantity} available · ${row.category || row.unit}`, pick: () => setAsset(row) }))} />}
					</>}
				</div>
				<div>
					<label className="block text-sm font-semibold">Volunteer</label>
					{volunteer ? <div className="mt-2 flex items-center justify-between gap-2 rounded-lg border p-3 text-sm"><span><strong>{volunteer.full_name}</strong> · {volunteer.home_geo_node}</span><button type="button" className="font-semibold text-blue" onClick={() => setVolunteer(null)}>Change</button></div> : <>
						<input className={`${INPUT} mt-2`} type="search" placeholder="Search name, email or volunteer ID" value={volunteerSearch} onChange={(event) => setVolunteerSearch(event.target.value)} />
						{people.error && <ErrorNote>{errorMessage(people.error)}</ErrorNote>}
						{volunteerTerm.length >= 2 && volunteerSearch.trim() === volunteerTerm && <SearchResults loading={people.isLoading} empty="No active volunteers found in this branch" full={(people.data?.message.length ?? 0) === 20} rows={(people.data?.message ?? []).map((row) => ({ id: row.name, title: row.full_name, detail: `${row.home_geo_node} · ${row.name}`, pick: () => setVolunteer(row) }))} />}
					</>}
				</div>
			</div>
			<div className="flex flex-wrap items-center gap-2">
				<input className={`${INPUT} w-24`} aria-label="Quantity" type="number" min="1" step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
				<Button disabled={busy || !asset || !validQuantity} onClick={() => asset && act(API.assetReceive, { asset: asset.name, quantity }, "receive")}>Receive</Button>
				<Button disabled={busy || !asset || !volunteer || !asset.is_active || !validQuantity || Number(quantity) > asset.available_quantity} onClick={() => asset && volunteer && act(API.assetIssue, { asset: asset.name, volunteer: volunteer.name, quantity }, "issue")}>Issue to volunteer</Button>
			</div>
		</Card>}

		<Card className="space-y-4 p-5">
			{holdings.error && <ErrorNote>{errorMessage(holdings.error)}</ErrorNote>}
			<div className="flex flex-wrap items-end justify-between gap-3"><h2 className="text-lg font-semibold">Currently held by volunteers</h2><input className={`${INPUT} sm:w-72`} type="search" aria-label="Search issued equipment" placeholder="Search volunteer or asset" value={issueSearch} onChange={(event) => setIssueSearch(event.target.value)} /></div>
			{holdings.isLoading ? <Spinner label="Loading current issues…" /> : issues.length === 0 ? <p className="text-sm text-muted">No outstanding issues match this search.</p> : <div className="space-y-2">{issues.map((row) => <div key={row.name} className="flex flex-wrap items-center justify-between gap-3 border-t py-3 text-sm"><div><strong>{row.asset_name}</strong> · {row.volunteer_name} · {row.outstanding} outstanding · {row.geo_node}{row.last_reminded_at && <p className="text-xs text-muted">Last reminded {formatDate(row.last_reminded_at)}</p>}</div><div className="flex flex-wrap items-center gap-2"><input className={`${INPUT} w-20`} aria-label={`Return quantity for ${row.asset_name}`} type="number" min="1" max={row.outstanding} step="1" value={returnAmounts[row.name] ?? String(row.outstanding)} onChange={(event) => setReturnAmounts({ ...returnAmounts, [row.name]: event.target.value })} /><Button disabled={busy || Number(returnAmounts[row.name] ?? row.outstanding) < 1 || Number(returnAmounts[row.name] ?? row.outstanding) > row.outstanding || !Number.isInteger(Number(returnAmounts[row.name] ?? row.outstanding))} onClick={() => act(API.assetReturn, { issue: row.name, quantity: returnAmounts[row.name] ?? row.outstanding }, "return")}>Record return</Button><Button variant="soft" disabled={busy} onClick={() => act(API.assetRemind, { issue: row.name }, "remind")}>Send reminder</Button></div></div>)}</div>}
			{issues.length === 50 && <p className="text-sm text-muted">Showing the latest 50 matches. Search by volunteer or asset to narrow the list.</p>}
		</Card>
	</div>;
}

function SearchResults({ rows, loading, empty, full }: { rows: Array<{ id: string; title: string; detail: string; pick: () => void }>; loading: boolean; empty: string; full: boolean }) {
	return <div className="mt-2 rounded-lg border border-card-line bg-white p-1 text-sm">
		{loading ? <p className="p-2 text-muted">Searching…</p> : rows.length === 0 ? <p className="p-2 text-muted">{empty}</p> : <ul className="max-h-64 overflow-y-auto">{rows.map((row) => <li key={row.id}><button type="button" className="w-full rounded-md p-2 text-left hover:bg-surface focus:bg-surface" onClick={row.pick}><strong className="block">{row.title}</strong><span className="text-muted">{row.detail}</span></button></li>)}</ul>}
		{full && <p className="border-t p-2 text-xs text-muted">Showing 20 matches. Type more to narrow the search.</p>}
	</div>;
}
