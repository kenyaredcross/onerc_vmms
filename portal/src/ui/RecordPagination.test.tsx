import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { useRecordPage } from './RecordPagination';

describe('record pagination', () => {
 it('caps pages at 25 and resets after filtering without losing pages on edits', () => {
  const rows=Array.from({length:61},(_,i)=>({name:String(i),label:'Task'}));
  const {result,rerender}=renderHook(({items})=>useRecordPage(items,100),{initialProps:{items:rows}});
  expect(result.current.slice).toHaveLength(25);
  act(()=>result.current.onPage(2));
  expect(result.current.slice).toHaveLength(11);
  rerender({items:rows.map(row=>({...row,label:'Updated'}))});
  expect(result.current.page).toBe(2);
  rerender({items:rows.slice(0,26)});
  expect(result.current.page).toBe(0);
  expect(result.current.total).toBe(26);
 });
});
