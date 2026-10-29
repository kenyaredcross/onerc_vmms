import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "../../ui/icons";
export function AssetOverlay({ title, description, drawer = false, onClose, children }: { title: string; description: string; drawer?: boolean; onClose: () => void; children: ReactNode }) {
 const ref = useRef<HTMLDialogElement>(null);
 useEffect(() => { const node=ref.current;node?.showModal();return () => node?.close(); }, []);
 return <dialog ref={ref} className={`asset-overlay ${drawer ? "is-drawer" : ""}`} aria-label={title} onCancel={onClose} onClick={e => { if(e.currentTarget===e.target)onClose(); }}>
  <header><div><h2>{title}</h2><p>{description}</p></div><button type="button" aria-label={`Close ${title.toLowerCase()}`} onClick={onClose}><Icon.cross size={18} /></button></header>
  {children}
 </dialog>;
}
