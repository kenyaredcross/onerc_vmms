import { useRecordPage, RecordPager } from "../../ui/RecordPagination";
import { useContext, useState } from "react";
import { FrappeContext } from "frappe-react-sdk";
import { API, errorMessage } from "../../lib/api";
import { taskStage, taskStages as stages } from "../../lib/task-board";
import { TaskDialog } from "./TaskDialog";
import type { TaskSummary, TaskChecklistItem } from "../../portal/types";
import { TaskCard } from "./TaskCard";
import { TaskRows } from "./TaskRows";
import { Icon } from "../../ui/icons";


export type BoardTask = TaskSummary & { full_name: string; board_stage?: string; thread_count?: number; description?:string; checklist?: TaskChecklistItem[] };
export function TaskBoard({ tasks, onOpen, onAssign, onChanged, href, volunteerView = false, searchValue, onSearchChange }: { tasks: BoardTask[]; onOpen?: (name: string) => void; onAssign?: () => void; onChanged?: () => void; href?: (name: string) => string; volunteerView?: boolean; searchValue?: string; onSearchChange?: (value: string) => void }) {
 const { call } = useContext(FrappeContext)!;
 const [moving, setMoving] = useState("");
 const [dragging, setDragging] = useState("");
 const [over, setOver] = useState("");
 const [moveError, setMoveError] = useState("");
 const [returnTask, setReturnTask] = useState<BoardTask | null>(null);
 const [reason, setReason] = useState("");
 const moveTask = async (task: BoardTask, stage: string, note?: string) => {
  if (volunteerView) return;
  setMoveError("");
  if(stage === taskStage(task))return;
  if(task.status === "submitted" && stage === "progress" && !note) { setReturnTask(task);setReason("");return; }
  setMoving(task.name);
  try { await call.post(API.moveBoardTask, { name: task.name, stage, reason: note }); setReturnTask(null); onChanged?.(); }
  catch(error) { setMoveError(error instanceof Error ? error.message : errorMessage(error, "The task could not be moved.")); }
  finally { setMoving("");setDragging("");setOver(""); }
 };
 const dragStart = (task: BoardTask) => { setDragging(task.name);setMoveError(""); };
 const dragEnd = () => { setDragging("");setOver(""); };
 const [view, setView] = useState<"Board" | "List" | "Table">("List");
 const [pageSize, setPageSize] = useState(10);
 const [selected, setSelected] = useState<Set<string>>(new Set());
 const [localQuery, setLocalQuery] = useState("");
 const query = searchValue ?? localQuery;
 const setQuery = onSearchChange ?? setLocalQuery;
 const [priority, setPriority] = useState("");
 const [volunteer, setVolunteer] = useState("");
 const [sort, setSort] = useState("attention");
 const rows = tasks.filter(t => (!priority || t.priority === priority) && (!volunteer || t.volunteer === volunteer) && `${t.subject} ${t.full_name} ${t.name} ${t.geo_node} ${t.task_type ?? ""}`.toLowerCase().includes(query.trim().toLowerCase()))
  .sort((a,b) => sort === "name" ? a.subject.localeCompare(b.subject) : sort === "priority" ? ["Urgent","High","Medium","Normal","Low"].indexOf(a.priority || "Normal") - ["Urgent","High","Medium","Normal","Low"].indexOf(b.priority || "Normal") : (sort === "attention" ? Number(!a.is_open) - Number(!b.is_open) : 0) || (a.due_on || "9999").localeCompare(b.due_on || "9999"));
 const paging = useRecordPage(rows, pageSize, 50);
 const select = (names: string[], checked: boolean) => setSelected(previous => {
  const next = new Set(previous);
  for (const name of names) { if (checked) next.add(name); else next.delete(name); }
  return next;
 });
 const owners = [...new Map(tasks.map(t => [t.volunteer, t.full_name])).entries()].sort((a,b) => a[1].localeCompare(b[1]));
 return <div className="tasks-workspace">
  <div className="tasks-toolbar">
   <div className="tasks-view-switch" role="group" aria-label="Task view">{(["List", "Board", "Table"] as const).map(v => <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>{v === "Board" ? <Icon.columns size={14} /> : v === "List" ? <Icon.menu size={14} /> : <Icon.grid size={14} />}{v}</button>)}</div>
   <label className="tasks-search"><Icon.search size={15} /><input aria-label="Search tasks" placeholder="Search tasks…" value={query} onChange={e => setQuery(e.target.value)} /></label>
   <details className="tasks-filter"><summary><Icon.filter size={15} />Filter{(priority || volunteer) && <span className="tasks-filter-dot" />}</summary><div>
    {!volunteerView && <label>Assignee<select aria-label="Filter by assignee" value={volunteer} onChange={e => setVolunteer(e.target.value)}><option value="">All volunteers</option>{owners.map(([id,name]) => <option value={id} key={id}>{name}</option>)}</select></label>}
    <label>Priority<select aria-label="Filter by priority" value={priority} onChange={e => setPriority(e.target.value)}><option value="">All priorities</option>{[...new Set(tasks.map(t => t.priority).filter(Boolean))].map(p => <option key={p!}>{p}</option>)}</select></label>
    <button type="button" onClick={() => {setPriority("");setVolunteer("");}}>Clear filters</button>
   </div></details>
   <select className="tasks-sort" aria-label="Sort tasks" value={sort} onChange={e => setSort(e.target.value)}><option value="attention">Active tasks first</option><option value="due">Due date</option><option value="priority">Priority</option><option value="name">Task name</option></select>
   {onAssign && <button className="tasks-add" type="button" onClick={onAssign}><Icon.plus size={15} />Assign task</button>}
  </div>
  <p className="tasks-count" role="status">{rows.length} of {tasks.length} tasks · {tasks.filter(t => t.status === "submitted").length} awaiting review · {tasks.filter(t => t.open_question && t.is_open).length} questions</p>
  {moveError && <p className="task-move-error" role="alert">{moveError}</p>}
  {returnTask && <TaskDialog title="Return task for more work" onClose={() => { setReturnTask(null);setMoveError(""); }}><label className="task-return-reason">Reason<textarea value={reason} onChange={e => setReason(e.target.value)} /></label>{moveError && <p role="alert" className="task-move-error">{moveError}</p>}<button type="button" className="tasks-add" disabled={!reason.trim() || !!moving} onClick={() => void moveTask(returnTask, "progress", reason)}>Return task</button></TaskDialog>}
  {view === "Board" ? <div className="task-board-scroll" tabIndex={0} aria-label="Task board columns"><div className="task-board">
   {stages.filter(s => s.key !== "closed" || tasks.some(t => taskStage(t) === "closed")).map(stage => {
    const column = paging.slice.filter(t => taskStage(t) === stage.key);
    return <section key={stage.key} className={`task-column ${over === stage.key ? "is-drop-target" : ""}`} aria-label={stage.label} data-stage={stage.key}
     onDragOver={event => { if(!volunteerView && dragging) { event.preventDefault();event.dataTransfer.dropEffect="move";setOver(stage.key); } }}
     onDrop={event => { if(volunteerView)return; event.preventDefault(); const id=event.dataTransfer.getData("text/plain");const task=tasks.find(t => t.name === id);setOver("");setDragging("");if(task)void moveTask(task, stage.key); }}>
     <header><div><h2>{stage.label}</h2><span>{column.length}{paging.pageCount > 1 ? ` of ${rows.filter(task => taskStage(task) === stage.key).length}` : ""} {column.length === 1 && paging.pageCount === 1 ? "task" : "tasks"}</span></div>{stage.key === "assigned" && onAssign && <button type="button" aria-label="Assign a new task" onClick={onAssign}><Icon.plus size={15} /></button>}</header>
     <div className="task-column-cards">{column.map(task => <TaskCard key={task.name} task={task} onOpen={onOpen} onMove={moveTask} onDragStart={dragStart} onDragEnd={dragEnd} moving={!!moving} canMove={!volunteerView} href={href} />)}{!column.length && <p className="task-column-empty">No tasks on this page</p>}</div>
    </section>;
   })}
  </div></div> : <TaskRows tasks={paging.slice} onOpen={onOpen} href={href} view={view} selected={selected} onSelect={select} />}
  <RecordPager {...paging} onPageSize={setPageSize} selectedCount={view === "Table" ? rows.filter(task => selected.has(task.name)).length : undefined} />
  {!rows.length && view !== "Board" && <p className="tasks-no-results">No matching tasks. Try another search or clear the filters.</p>}
 </div>;
}
