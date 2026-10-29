import { useContext, useState, type FormEvent } from "react";
import { FrappeContext, useFrappeFileUpload } from "frappe-react-sdk";
import { API } from "../../lib/api";
import { Icon } from "../../ui/icons";
import { AssetOverlay } from "./AssetOverlay";
import type { Asset } from "./types";
export function AssetForm({ asset, branches, categories, branch, onClose, onSaved }: { asset?: Asset; branches: string[]; categories: string[]; branch: string; onClose: () => void; onSaved: (text: string) => void }) {
 const { call }=useContext(FrappeContext)!, { upload }=useFrappeFileUpload();
 const [images,setImages]=useState(asset?.images || []), [error,setError]=useState(""),[busy,setBusy]=useState(false),[uploading,setUploading]=useState(false);
 const [active,setActive]=useState(asset?.is_active !== 0);
 const save=async(event: FormEvent<HTMLFormElement>)=>{
  event.preventDefault();setError("");const data=Object.fromEntries(new FormData(event.currentTarget));setBusy(true);
  try { await call.post(asset ? API.assetUpdate : API.assetCreate,{...data,geo_node:data.geo_node || asset?.geo_node || branch,name:asset?.name,images,is_active:active?1:0});onSaved(asset?"Asset updated.":"Asset added."); }
  catch(e){setError(e instanceof Error?e.message:"The asset could not be saved.");}finally{setBusy(false);}
 };
 const addImages=async(files: FileList | null)=>{
  if(!files)return;const selected=Array.from(files);setError("");
  if(images.length+selected.length>5||selected.some(f=>!["image/jpeg","image/png","image/webp"].includes(f.type)||f.size===0||f.size>5*1024*1024)){setError("Use up to 5 JPG, PNG or WebP images, each no larger than 5 MB.");return;}
  setUploading(true);try{const added: string[]=[];for(const file of selected)added.push((await upload(file, { isPrivate: true })).file_url);setImages(current=>[...current,...added]);}catch{setError("The image could not be attached.");}finally{setUploading(false);}
 };
 return <AssetOverlay title={asset?"Edit asset":"Add asset"} description={asset?"Update the asset details and availability.":"Enter asset details, branch and opening stock."} drawer={false} onClose={onClose}>
  <form className="asset-form" onSubmit={save}>
   <div className="asset-form-fields">
    {error && <p role="alert" className="asset-form-error">{error}</p>}
    <label>Asset name<input name="asset_name" defaultValue={asset?.asset_name} placeholder="e.g. First aid kit" required maxLength={100} /></label>
    {!asset && <label>Description<textarea name="description" placeholder="Describe the asset and its use." rows={3} maxLength={2000} /></label>}
    {!asset && <div className="asset-images"><span>Images <small>(optional)</small></span><label className="asset-image-drop"><Icon.upload size={22} /><strong>{uploading?"Attaching images…":"Click to upload images"}</strong><small>JPG, PNG or WebP · Up to 5 images · 5 MB each</small><input type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={uploading || images.length>=5} onChange={e=>void addImages(e.target.files)} /></label>{images.length>0 && <div className="asset-image-previews">{images.map((src,i)=><div key={src}><img src={src} alt={`Asset image ${i+1}`} /><button type="button" aria-label={`Remove image ${i+1}`} onClick={()=>setImages(images.filter((_,index)=>index!==i))}><Icon.cross size={12} /></button></div>)}</div>}</div>}
    {asset && <label>Asset code<input value={asset.name} readOnly /></label>}
    <div className="asset-form-grid">
     <label>Category<select aria-label="Category" name="category" defaultValue={asset?.category || categories[0]} required>{categories.map(c=><option key={c}>{c}</option>)}</select></label>
     <label>Status<select aria-label="Status" value={active?"Active":"Inactive"} onChange={e=>setActive(e.target.value==="Active")}><option>Active</option><option>Inactive</option></select></label>
     <label>Unit<input name="unit" defaultValue={asset?.unit || "Piece"} required maxLength={30} /></label>
     <label>Branch<select aria-label="Branch" name="geo_node" defaultValue={asset?.geo_node || branch || branches[0]} required disabled={!!asset && asset.total_quantity>asset.available_quantity}>{branches.map(b=><option key={b}>{b}</option>)}</select>{asset && asset.total_quantity>asset.available_quantity && <small>Return issued items before changing branch.</small>}</label>
     {!asset && <label>Opening quantity<input name="quantity" type="number" min={0} max={1000000} step={1} defaultValue={0} required /></label>}
    </div>
    {asset && <p className="asset-form-hint">{asset.available_quantity} available of {asset.total_quantity} {asset.unit.toLowerCase()}. Use Receive stock to add inventory.</p>}
   </div>
   <footer><button type="button" onClick={onClose}>Cancel</button><button type="submit" className="asset-primary" disabled={busy || uploading}>{busy?"Saving…":asset?"Save changes":"Add asset"}</button></footer>
  </form>
 </AssetOverlay>;
}
