import type { Asset } from "./types";
export function AssetInsights({assets}:{assets:Asset[]}) {
 const total=assets.reduce((sum,a)=>sum+a.total_quantity,0),available=assets.reduce((sum,a)=>sum+a.available_quantity,0),issued=total-available;
 const counts=new Map<string,number>();for(const a of assets)counts.set(a.category||"Uncategorised",(counts.get(a.category||"Uncategorised")||0)+1);
 const groups=[...counts].sort((a,b)=>b[1]-a[1]),shown=groups.slice(0,5);if(groups.length>5)shown.push(["Other",groups.slice(5).reduce((sum,row)=>sum+row[1],0)]);
 const max=Math.max(1,...shown.map(row=>row[1])),circumference=2*Math.PI*45;
 return <details className="asset-insights" open><summary>Inventory overview <span>{assets.length} assets · Current filters</span></summary><div className="asset-insight-grid">
  <section className="asset-stock-chart"><div><h2>Stock availability</h2><p>Available and issued stock units</p></div><div className="asset-stock-visual">
   <svg viewBox="0 0 120 120" role="img" aria-label={`${available} available, ${issued} issued out of ${total} stock units`}>
    <circle cx="60" cy="60" r="45" fill="none" stroke={total?"#011E41":"#E6EAF0"} strokeWidth="13" />
    {total>0&&<circle cx="60" cy="60" r="45" fill="none" stroke="#C53043" strokeWidth="13" strokeDasharray={`${issued/total*circumference} ${circumference}`} transform="rotate(-90 60 60)" />}
    <text x="60" y="59" textAnchor="middle" className="asset-donut-value">{total.toLocaleString()}</text><text x="60" y="75" textAnchor="middle" className="asset-donut-label">total units</text>
   </svg><dl><div><dt><i className="available" />Available</dt><dd>{available.toLocaleString()}</dd></div><div><dt><i className="issued" />Issued</dt><dd>{issued.toLocaleString()}</dd></div><div className="asset-stock-rate"><dt>Availability</dt><dd>{total?Math.round(available/total*100):0}%</dd></div></dl>
  </div></section>
  <section className="asset-category-chart"><h2>Assets by category</h2><p>Asset records in the current inventory</p><div>{shown.map(([label,count])=><div className="asset-category-bar" key={label}><span title={label}>{label}</span><div role="img" aria-label={`${label}: ${count} assets`}><span style={{width:`${count/max*100}%`}} /></div><strong>{count}</strong></div>)}{!shown.length&&<p>No assets match the current filters.</p>}</div></section>
 </div></details>;
}
