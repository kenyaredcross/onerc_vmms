import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "../../ui/icons";
export function TaskDialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
 const dialog = useRef<HTMLDialogElement>(null);
 useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
 return <dialog className="task-dialog" ref={dialog} aria-label={title} onCancel={onClose} onClick={event => { if(event.target === event.currentTarget)onClose(); }}>
  <header><h2>{title}</h2><button type="button" onClick={onClose} aria-label="Close task"><Icon.cross size={18} /></button></header>
  <div className="task-dialog-content">{children}</div>
 </dialog>;
}
