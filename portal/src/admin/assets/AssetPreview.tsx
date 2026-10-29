import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "../../ui/icons";
import type { Asset } from "./types";

export function AssetPreview({ asset, anchor, onClose, onEdit }: { asset:Asset; anchor:HTMLElement; onClose:()=>void; onEdit:()=>void }) {
 const [visible,setVisible]=useState(false),[position,setPosition]=useState<{top:number;left:number}|null>(null);
 const card=useRef<HTMLDivElement>(null);
 useEffect(()=>{const timer=setTimeout(()=>setVisible(true),250);return ()=>clearTimeout(timer);},[]);
 useLayoutEffect(()=>{
  if(!visible||!card.current)return;
  const panel=card.current,box=panel.getBoundingClientRect(),rect=(anchor.querySelector('td:nth-child(2)')||anchor).getBoundingClientRect();
  const scale=panel.offsetWidth?box.width/panel.offsetWidth:1;
  const left=Math.max(8,Math.min(rect.left,window.innerWidth-box.width-8));
  const top=rect.bottom+box.height+8<=window.innerHeight?rect.bottom:Math.max(8,rect.top-box.height);
  setPosition({top:top/scale,left:left/scale});
 },[visible,anchor]);
 useEffect(()=>{
  const dismiss=(event:KeyboardEvent)=>{if(event.key==='Escape'){if(card.current?.contains(document.activeElement))anchor.focus();onClose();}};
  const outside=(event:MouseEvent)=>{if(!anchor.contains(event.target as Node)&&!card.current?.contains(event.target as Node))onClose();};
  const moved=()=>onClose();
  document.addEventListener('keydown',dismiss);document.addEventListener('mousedown',outside);window.addEventListener('resize',moved);window.addEventListener('scroll',moved,true);
  return ()=>{document.removeEventListener('keydown',dismiss);document.removeEventListener('mousedown',outside);window.removeEventListener('resize',moved);window.removeEventListener('scroll',moved,true);};
 },[anchor,onClose]);
 if(!visible)return null;
 return createPortal(<div ref={card} className="asset-hover-preview" data-asset-preview role="dialog" aria-label="Asset summary"
  style={{top:position?.top||0,left:position?.left||0,visibility:position?'visible':'hidden'}}
  onMouseLeave={event=>{if(!(event.relatedTarget instanceof Node&&anchor.contains(event.relatedTarget)))onClose();}}>
  <header>{asset.images?.[0]?<img src={asset.images[0]} alt="" />:<span><Icon.inbox size={24} /></span>}<div><h2>{asset.asset_name}</h2><p>{asset.geo_node}</p><span>{asset.is_active?'Active':'Inactive'}</span></div></header>
  <dl>{[['Asset code',asset.name],['Category',asset.category||'—'],['Unit',asset.unit],['Total stock',asset.total_quantity],['Available',asset.available_quantity],['Issued',asset.total_quantity-asset.available_quantity]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
  <button type="button" onClick={onEdit}>Edit asset <Icon.arrow size={14} /></button>
 </div>,document.body);
}
