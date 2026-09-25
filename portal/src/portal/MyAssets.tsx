import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";
import { API, errorMessage } from "../lib/api";
import { Button, Card, Empty, ErrorNote, PageHeading, Spinner } from "../ui/primitives";

type Issue = { name: string; asset_name: string; geo_node: string; quantity: number; outstanding: number; occurred_at: string };

export default function MyAssets() {
  const { call } = useContext(FrappeContext) as FrappeConfig;
  const list = useFrappeGetCall<{ message: Issue[] }>(API.myAssets, undefined, "portal:my_assets");
  const [busy, setBusy] = useState("");
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState("");
  async function returnItem(row: Issue) {
    setBusy(row.name); setFailure("");
    try { await call.post(API.returnMyAsset, { issue: row.name, quantity: amounts[row.name] ?? row.outstanding }); await list.mutate(); setAmounts({}); }
    catch (error) { setFailure(errorMessage(error)); }
    finally { setBusy(""); }
  }
  const rows = list.data?.message ?? [];
  return <div className="space-y-6">
    <PageHeading title="My equipment" lead="See what your branch has issued to you and record a return." />
    {failure && <ErrorNote>{failure}</ErrorNote>}
    {list.isLoading ? <Spinner label="Loading equipment…" /> : rows.length === 0 ? <Empty title="No equipment held">Your current branch issues will appear here.</Empty> : <div className="space-y-3">{rows.map((row) => <Card key={row.name} className="flex flex-wrap items-center justify-between gap-3 p-5"><div><strong>{row.asset_name}</strong><p className="text-sm text-muted">{row.outstanding} held · {row.geo_node}</p></div><span className="flex items-center gap-2"><input className="w-20 rounded-lg border p-2" aria-label={`Return quantity for ${row.asset_name}`} type="number" min="1" max={row.outstanding} step="1" value={amounts[row.name] ?? String(row.outstanding)} onChange={(event) => setAmounts({ ...amounts, [row.name]: event.target.value })} /><Button disabled={!!busy || Number(amounts[row.name] ?? row.outstanding) < 1 || Number(amounts[row.name] ?? row.outstanding) > row.outstanding || !Number.isInteger(Number(amounts[row.name] ?? row.outstanding))} onClick={() => returnItem(row)}>Record return</Button></span></Card>)}</div>}
  </div>;
}
