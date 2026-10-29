import { Children, Fragment, isValidElement, useState, type ReactNode } from "react";

export const MAX_RECORDS_PER_PAGE = 25;

function recordIdentity(row: unknown, index: number) {
 if (row && typeof row === "object") {
  const record = row as Record<string, unknown>;
  return record.key ?? record.name ?? record.id ?? record.event ?? record.assignment ?? index;
 }
 return row ?? index;
}

/** Preserve the page during record updates; reset it when filtering or ordering changes. */
export function useRecordPage<T>(rows: T[], size = MAX_RECORDS_PER_PAGE, maxSize = MAX_RECORDS_PER_PAGE) {
 const pageSize = Math.max(1, Math.min(maxSize, Math.floor(size) || MAX_RECORDS_PER_PAGE));
 const signature = JSON.stringify([pageSize, rows.map(recordIdentity)]);
 const [state, setState] = useState({ signature, page: 0 });
 const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
 const page = state.signature === signature ? Math.min(state.page, pageCount - 1) : 0;
 if (state.signature !== signature || page !== state.page) setState({ signature, page });
 return { page, pageCount, pageSize, total: rows.length, slice: rows.slice(page * pageSize, (page + 1) * pageSize),
  onPage: (next: number) => setState({ signature, page: Math.max(0, Math.min(next, pageCount - 1)) }) };
}

export function RecordPager({ page, pageCount, pageSize = 25, total, onPage, onPageSize, selectedCount }: {
 page: number; pageCount: number; pageSize?: number; total: number; onPage: (page: number) => void;
 onPageSize?: (size: number) => void; selectedCount?: number;
}) {
 if (onPageSize) return <TaskPager page={page} pageCount={pageCount} pageSize={pageSize} total={total} onPage={onPage} onPageSize={onPageSize} selectedCount={selectedCount} />;
 if (pageCount <= 1) return null;
 const start = Math.max(0, Math.min(page - 2, pageCount - 5));
 return <nav className="record-pagination" aria-label="Record pages">
  <span role="status">{page * pageSize + 1}–{Math.min(total, (page + 1) * pageSize)} of {total}</span>
  <div><button type="button" disabled={page === 0} onClick={() => onPage(page - 1)} aria-label="Previous page">Previous</button>
  {Array.from({ length: Math.min(5, pageCount) }, (_, index) => start + index).map(index => <button type="button" key={index} aria-label={`Page ${index + 1}`} aria-current={index === page ? "page" : undefined} onClick={() => onPage(index)}>{index + 1}</button>)}
  <button type="button" disabled={page === pageCount - 1} onClick={() => onPage(page + 1)} aria-label="Next page">Next</button></div>
 </nav>;
}

function TaskPager({ page, pageCount, pageSize, total, onPage, onPageSize, selectedCount }: {
 page: number; pageCount: number; pageSize: number; total: number;
 onPage: (page: number) => void; onPageSize: (size: number) => void; selectedCount?: number;
}) {
 const start = Math.max(0, Math.min(page - 1, pageCount - 3));
 const numbers = Array.from({ length: Math.min(3, pageCount) }, (_, index) => start + index);
 return <nav className="task-pagination" aria-label="Task pages">
  <span className="task-pagination-summary" role="status">{selectedCount === undefined
   ? `${total ? page * pageSize + 1 : 0}–${Math.min(total, (page + 1) * pageSize)} of ${total} tasks`
   : `${selectedCount} of ${total} row(s) selected.`}</span>
  <div className="task-pagination-controls">
   <label>Rows per page<select aria-label="Rows per page" value={pageSize} onChange={e => onPageSize(Number(e.target.value))}>{[10,20,30,40,50].map(size => <option key={size} value={size}>{size}</option>)}</select></label>
   <span className="task-pagination-position">Page {page + 1} of {pageCount}</span>
   <div className="task-pagination-pages">
    <button type="button" disabled={page === 0} onClick={() => onPage(0)} aria-label="First page">«</button>
    <button type="button" disabled={page === 0} onClick={() => onPage(page - 1)} aria-label="Previous page">‹ <span>Prev</span></button>
    {start > 0 && <span aria-hidden="true">…</span>}
    {numbers.map(index => <button type="button" key={index} aria-label={`Page ${index + 1}`} aria-current={index === page ? 'page' : undefined} onClick={() => onPage(index)}>{index + 1}</button>)}
    {start + numbers.length < pageCount && <span aria-hidden="true">…</span>}
    <button type="button" disabled={page === pageCount - 1} onClick={() => onPage(page + 1)} aria-label="Next page"><span>Next</span> ›</button>
    <button type="button" disabled={page === pageCount - 1} onClick={() => onPage(pageCount - 1)} aria-label="Last page">»</button>
   </div>
  </div>
 </nav>;
}

export function recordChildren(children: ReactNode): ReactNode[] {
 return Children.toArray(children).flatMap(child => isValidElement<{children?: ReactNode}>(child) && child.type === Fragment ? recordChildren(child.props.children) : [child]);
}

/** Pagination around existing record layouts, without changing their cards or rows. */
export function RecordCollection({ as: Tag = "div", children, ...props }: { as?: "div" | "ul"; children: ReactNode; className?: string }) {
 const paging = useRecordPage(recordChildren(children));
 return <><Tag {...props}>{paging.slice}</Tag><RecordPager {...paging} /></>;
}
