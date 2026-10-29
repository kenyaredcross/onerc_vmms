import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatDate } from "../../lib/format";
import { taskStage, taskStages } from "../../lib/task-board";
import { Icon } from "../../ui/icons";
import type { BoardTask } from "./TaskBoard";

export function TaskOpen({ task, onOpen, href, children, className }: {
 task: BoardTask; onOpen?: (name: string) => void; href?: (name: string) => string;
 children: ReactNode; className?: string;
}) {
 const label = `Open ${task.subject}, assigned to ${task.full_name}`;
 return href ? <Link className={className} to={href(task.name)} aria-label={label}>{children}</Link>
  : <button type="button" className={className} onClick={() => onOpen?.(task.name)} aria-label={label}>{children}</button>;
}

export function TaskPriority({ priority, compact = false }: { priority: string | null; compact?: boolean }) {
 const level = (priority || 'Normal').toLowerCase();
 return <span className={`task-priority priority-${level}${compact ? ' task-priority-plain' : ''}`}>
  {compact && <Icon.arrow size={14} className={level === 'high' || level === 'urgent' ? '-rotate-90' : level === 'low' ? 'rotate-90' : ''} />}
  {priority || 'Normal'}
 </span>;
}
export function TaskOwner({ name }: { name: string }) {
 return <span className="task-assignee"><span className="task-person-initials" aria-hidden="true">{name.split(/\s+/).slice(0, 2).map(word => word[0]).join('')}</span><span>{name}</span></span>;
}
export function TaskStage({ task }: { task: BoardTask }) {
 const stage = taskStage(task);
 const paths: Record<string, string> = {
  assigned: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  accepted: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM8 12l3 3 5-6',
  progress: 'M19 14a7 7 0 1 1-14 0 7 7 0 0 1 14 0ZM12 10v4l2-2M10 3h4m-2 0v4m5 1 2-2',
  submitted: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v5l3 2',
  completed: 'M21 11v1a9 9 0 1 1-5.3-8.2M8 11l4 4L22 5',
  closed: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM5.6 5.6l12.8 12.8',
 };
 return <span className={`task-stage stage-${stage}`}>
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[stage] || paths.assigned} /></svg>
  {taskStages.find(item => item.key === stage)?.label || task.status}
 </span>;
}
export function TaskDue({ task }: { task: BoardTask }) {
 return <span className={`task-due ${task.is_overdue ? 'task-overdue' : ''}`}>{task.due_on ? formatDate(task.due_on) : 'No due date'}<Icon.calendar size={13} /></span>;
}

export function TaskRows({ tasks, onOpen, href, view, selected, onSelect }: {
 tasks: BoardTask[]; onOpen?: (name: string) => void; href?: (name: string) => string;
 view: 'List' | 'Table'; selected: Set<string>; onSelect: (names: string[], checked: boolean) => void;
}) {
 const selectAll = useRef<HTMLInputElement>(null);
 const all = tasks.length > 0 && tasks.every(task => selected.has(task.name));
 const some = tasks.some(task => selected.has(task.name));
 useEffect(() => { if (selectAll.current) selectAll.current.indeterminate = some && !all; }, [some, all]);
 if (view === 'List') return <div className="tasks-list">
  <div className="task-list-head">
   <span className="task-list-id">Task</span><span>Title</span><span>Status</span><span className="task-list-priority-heading">Priority</span><span className="task-list-assignee-heading">Assignee</span><span>Due date</span><span />
  </div>
  <ul aria-label="Task list">
  {tasks.map(task => <li className="task-list-row" key={task.name} data-task={task.name}>
   <TaskOpen task={task} onOpen={onOpen} href={href} className="task-list-open">
    <span className="task-list-id">{task.name}</span>
    <span className="task-list-title">{task.task_type && <span className="task-list-type" title={task.task_type}>{task.task_type}</span>}<strong title={task.subject}>{task.subject}</strong></span>
    <TaskStage task={task} /><TaskPriority priority={task.priority} compact />
    <TaskOwner name={task.full_name} /><TaskDue task={task} />
    <Icon.chevron size={16} className="-rotate-90" />
   </TaskOpen>
  </li>)}
  </ul>
 </div>;
 return <div className="tasks-table-scroll"><table className="tasks-table" aria-label="Tasks">
  <thead><tr><th><input ref={selectAll} type="checkbox" aria-label="Select this page" checked={all} disabled={!tasks.length} onChange={e => onSelect(tasks.map(task => task.name), e.target.checked)} /></th>
   {['Task', 'Assignee', 'Status', 'Priority', 'Due date', 'Progress'].map(label => <th key={label} scope="col">{label}</th>)}
  </tr></thead>
  <tbody>{tasks.map(task => <tr key={task.name} data-task={task.name} data-selected={selected.has(task.name)}>
   <td><input type="checkbox" aria-label={`Select ${task.subject}`} checked={selected.has(task.name)} onChange={e => onSelect([task.name], e.target.checked)} /></td>
   <td><TaskOpen task={task} onOpen={onOpen} href={href}>{task.subject}</TaskOpen><small>{task.name}</small></td>
   <td><TaskOwner name={task.full_name} /></td><td><TaskStage task={task} /></td>
   <td><TaskPriority priority={task.priority} /></td><td><TaskDue task={task} /></td>
   <td><span className="task-table-progress"><progress max={100} value={Math.min(100, Math.max(0, task.percent_complete || 0))} aria-label={`${task.subject} progress`} />{task.percent_complete || 0}%</span></td>
  </tr>)}</tbody>
 </table></div>;
}
