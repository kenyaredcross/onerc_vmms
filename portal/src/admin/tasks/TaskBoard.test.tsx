import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { mount } from '../../test/harness';
import { TaskBoard, type BoardTask } from './TaskBoard';

const tasks: BoardTask[] = Array.from({ length: 31 }, (_, i) => ({
 name: `TASK-${i + 1}`, subject: `Task ${String(i + 1).padStart(2, '0')}`, full_name: 'Asha Juma',
 volunteer: 'VOL-1', geo_node: 'Nairobi', status: i % 2 ? 'accepted' : 'assigned',
 due_on: '2026-10-30', due_at: null, assigned_on: null, open_question: false,
 is_open: true, priority: 'High', task_type: 'Field work', percent_complete: 0,
 is_overdue: false, description: 'Prepare the field visit and confirm transport.',
}));
function setup() {
 const onOpen = vi.fn();
 mount(<TaskBoard tasks={tasks} onOpen={onOpen} onAssign={vi.fn()} onChanged={vi.fn()} />);
 return { onOpen };
}
describe('task workspace views and pagination', () => {
 it('defaults to List with ten tasks and supports page size, last/first navigation, and filtering resets', () => {
  setup();
  expect(screen.getByRole('button', { name: 'List' }).getAttribute('aria-pressed')).toBe('true');
  expect(screen.getAllByRole('listitem')).toHaveLength(10);
  expect(document.querySelectorAll('[data-task]')).toHaveLength(10);
  expect(screen.getByText('Page 1 of 4')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Last page' }));
  expect(document.querySelectorAll('[data-task]')).toHaveLength(1);
  fireEvent.change(screen.getByLabelText('Rows per page'), { target: { value: '20' } });
  expect(screen.getByText('Page 1 of 2')).toBeTruthy();
  expect(document.querySelectorAll('[data-task]')).toHaveLength(20);
  fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
  fireEvent.change(screen.getByRole('textbox', { name: 'Search tasks' }), { target: { value: 'Task 01' } });
  expect(screen.getByText('Page 1 of 1')).toBeTruthy();
  expect(document.querySelectorAll('[data-task]')).toHaveLength(1);
  expect((screen.getByRole('button', { name: 'Next page' }) as HTMLButtonElement).disabled).toBe(true);
 });
 it('renders distinct list rows and selectable table rows while retaining the page across views', () => {
  const { onOpen } = setup();
  fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
  fireEvent.click(screen.getByRole('button', { name: 'List' }));
  expect(screen.getAllByRole('listitem')).toHaveLength(10);
  expect(document.querySelectorAll('.task-kanban-card')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: /Open Task 11/ }));
  expect(onOpen).toHaveBeenCalledWith('TASK-11');
  fireEvent.click(screen.getByRole('button', { name: 'Table' }));
  const table = screen.getByRole('table');
  expect(within(table).getAllByRole('row')).toHaveLength(11);
  expect(screen.getByText('Page 2 of 4')).toBeTruthy();
  fireEvent.click(screen.getByRole('checkbox', { name: 'Select this page' }));
  expect(screen.getByText('10 of 31 row(s) selected.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'First page' }));
  expect(screen.getByText('Page 1 of 4')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Rows per page'), { target: { value: '50' } });
  expect(within(table).getAllByRole('row')).toHaveLength(32);
 });
});
