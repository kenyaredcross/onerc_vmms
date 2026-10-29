import { describe, expect, it } from 'vitest';
import { taskStage, availableTaskMoves } from './task-board';
describe('task board workflow',()=>{
 it('shows accepted work with progress in progress and keeps completed work closed',()=>{
  expect(taskStage({status:'accepted',percent_complete:20})).toBe('progress');
  expect(availableTaskMoves({status:'assigned',percent_complete:0})).not.toContain('completed');
  expect(availableTaskMoves({status:'completed',percent_complete:100})).toEqual([]);
  expect(availableTaskMoves({status:'submitted',percent_complete:100})).toContain('completed');
 });
});
