import { availableTaskMoves, taskStage, taskStages as stages } from "../../lib/task-board";
import { Icon } from "../../ui/icons";
import { TaskDue, TaskOpen, TaskOwner, TaskPriority } from "./TaskRows";
import type { BoardTask } from "./TaskBoard";

export function TaskCard({ task, onOpen, onMove, onDragStart, onDragEnd, moving, href, canMove }: {
 task: BoardTask; onOpen?: (name:string) => void; onMove: (task: BoardTask, stage: string) => void;
 onDragStart: (task: BoardTask) => void; onDragEnd: () => void; moving: boolean; href?: (name: string) => string; canMove: boolean;
}) {
 const progress = taskStage(task) === "progress";
 const percent = Math.min(100, Math.max(0,task.percent_complete || 0));
 return <article className="task-kanban-card" data-task={task.name} draggable={canMove && !moving && availableTaskMoves(task).length > 0}
  onDragStart={event => { event.dataTransfer.setData("text/plain",task.name);event.dataTransfer.effectAllowed="move";event.currentTarget.classList.add("is-dragging");onDragStart(task); }}
  onDragEnd={event => { event.currentTarget.classList.remove("is-dragging");onDragEnd(); }}>
  <TaskOpen task={task} onOpen={onOpen} href={href} className="task-card-open">

  <div className="task-card-title"><h3 title={task.subject}>{task.subject}</h3><TaskPriority priority={task.priority} /></div>
  <p className="task-card-description">{task.description || task.task_type || task.subject}</p>
  {progress && <div className="task-card-progress"><span>Progress <strong>{percent}%</strong></span><progress value={percent} max={100} aria-label={`${task.subject} progress`} /></div>}
  {progress ? <div className="task-card-details">
   <div><span>Owner</span><TaskOwner name={task.full_name} /></div>
   <div><span>Due date</span><TaskDue task={task} /></div>
   <div><span>Branch</span><span className="task-branch">{task.geo_node}</span></div>
  </div> : <div className="task-card-person"><TaskOwner name={task.full_name} /><TaskDue task={task} /></div>}
  <footer>{task.status === "completed" ? <span className="task-done"><Icon.check size={14} />Completed</span> : <><span title="Task messages"><Icon.chat size={13} />{task.thread_count ?? 0}</span><span title="Checklist items"><Icon.check size={13} />{(task.checklist ?? []).filter(c => c.is_done).length}/{(task.checklist ?? []).length}</span>{task.open_question && <span className="task-question">Question</span>}{task.is_overdue && <span className="task-overdue">Overdue</span>}</>}</footer>
 </TaskOpen>
 {canMove && availableTaskMoves(task).length > 0 && <select className="task-card-move" aria-label={`Move ${task.subject}, ${task.full_name}`} title="Move task" value="" disabled={moving}
  onChange={event => { if(event.target.value)onMove(task,event.target.value); }}>
  <option value="">Move</option>{stages.filter(stage => availableTaskMoves(task).includes(stage.key)).map(stage => <option value={stage.key} key={stage.key}>{stage.label}</option>)}
 </select>}
 </article>;
}
