import { useContext, useState, type FormEvent } from "react";
import { FrappeContext, useFrappeGetCall } from "frappe-react-sdk";
import { API } from "../../lib/api";
import { AssetOverlay } from "./AssetOverlay";
import type { Asset, AssetIssue } from "./types";
export function AssetMovement({ mode, asset, issue, onClose, onSaved }: { mode:"receive"|"issue"|"return"; asset?: Asset; issue?: AssetIssue; onClose:()=>void; onSaved:(text:string)=>void }) {
 const {call}=useContext(FrappeContext)!,[busy,setBusy]=useState(false),[error,setError]=useState("");
 const [search,setSearch]=useState("");
 const volunteers=useFrappeGetCall<{message:{name:string;full_name:string}[]}>(API.assetSearchVolunteers,{geo_node:asset?.geo_node,search},mode==="issue"&&search.trim().length>=2?"asset-issue-people:"+asset?.geo_node+":"+search:null);
 const title=mode==="receive"?"Receive stock":mode==="issue"?"Issue to volunteer":"Record return";
 async function save(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError("");try{const data=Object.fromEntries(new FormData(e.currentTarget));await call.post(mode==="receive"?API.assetReceive:mode==="issue"?API.assetIssue:API.assetReturn,{...data,asset:asset?.name,issue:issue?.name});onSaved(mode==="return"?"Return recorded.":mode==="issue"?"Issue recorded.":"Stock received.");}catch(e){setError(e instanceof Error?e.message:"This action could not be saved.");}finally{setBusy(false);}}
 return <AssetOverlay title={title} description={`${asset?.asset_name || issue?.asset_name} · ${asset?.geo_node || issue?.geo_node}`} onClose={onClose}><form className="asset-form" onSubmit={save}><div className="asset-form-fields">
  {error && <p className="asset-form-error" role="alert">{error}</p>}
  {mode==="issue" && <label>Volunteer<input aria-label="Search volunteers" placeholder="Search by name, email or volunteer ID…" value={search} onChange={e=>setSearch(e.target.value)} /><select aria-label="Volunteer" name="volunteer" required defaultValue=""><option value="" disabled>Select a volunteer</option>{volunteers.data?.message.map(v=><option value={v.name} key={v.name}>{v.full_name}</option>)}</select></label>}
  {issue && <p>{issue.volunteer_name} · {issue.outstanding} outstanding</p>}
  <label>Quantity<input name="quantity" type="number" min={1} max={mode==="return"?issue?.outstanding:mode==="issue"?asset?.available_quantity:1000000} step={1} defaultValue={1} required /></label>
  {asset && <p className="asset-form-hint">{asset.available_quantity} {asset.unit.toLowerCase()} available.</p>}
 </div><footer><button type="button" onClick={onClose}>Cancel</button><button type="submit" className="asset-primary" disabled={busy}>{busy?"Saving…":title}</button></footer></form></AssetOverlay>;
}
