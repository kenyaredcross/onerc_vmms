import type { Asset, AssetIssue } from "./types";
function cell(value: unknown) {
 let text=String(value??"");
 // Spreadsheet programs must treat names and notes as data rather than formulas.
 if(/^[\s]*[=+@-]/.test(text))text="'"+text;
 return '"'+text.replaceAll('"','""')+'"';
}
export function exportAssets(rows: Asset[] | AssetIssue[], issued=false, selected=false) {
 const headers=issued?["Issue code","Asset","Volunteer","Branch","Issued on","Quantity issued","Outstanding","Last reminder"]:["Asset code","Asset","Category","Status","Branch","Unit","Total","Available","Issued"];
 const values=issued?(rows as AssetIssue[]).map(a=>[a.name,a.asset_name,a.volunteer_name,a.geo_node,a.issued_on||"",a.quantity,a.outstanding,a.last_reminded_at||""]):(rows as Asset[]).map(a=>[a.name,a.asset_name,a.category,a.is_active?"Active":"Inactive",a.geo_node,a.unit,a.total_quantity,a.available_quantity,a.total_quantity-a.available_quantity]);
 const csv="\uFEFF"+[headers,...values].map(row=>row.map(cell).join(",")).join("\r\n");
 const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8;"}));
 const link=document.createElement("a");link.href=url;link.download=`${issued?"issued-equipment":selected?"selected-assets":"assets"}-${new Date().toISOString().slice(0,10)}.csv`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
