import { act, type ReactNode } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { FrappeContext, type FrappeConfig } from 'frappe-react-sdk';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { API } from '../../lib/api';
import { AssetForm } from './AssetForm';

vi.mock('frappe-react-sdk',async()=>{
 const {createContext}=await import('react');
 return {FrappeContext:createContext(null),useFrappeFileUpload:()=>({upload:vi.fn()})};
});
vi.mock('./AssetOverlay',()=>({AssetOverlay:({children}:{children:ReactNode})=><div>{children}</div>}));
afterEach(()=>vi.restoreAllMocks());
describe('editing issued equipment',()=>{
 it('sends the existing branch even when its selector is disabled',async()=>{
  const post=vi.fn().mockResolvedValue({message:{}}),saved=vi.fn();
  render(<FrappeContext.Provider value={{call:{post}} as unknown as FrappeConfig}><AssetForm
   asset={{name:'ASSET-1',asset_name:'Radio',category:'Equipment',unit:'each',geo_node:'Branch A',total_quantity:5,available_quantity:2,is_active:1}}
   branches={['Branch A','Branch B']} categories={['Equipment']} branch='' onClose={()=>{}} onSaved={saved}
  /></FrappeContext.Provider>);
  expect((screen.getByRole('combobox',{name:'Branch'}) as HTMLSelectElement).disabled).toBe(true);
  await act(async()=>fireEvent.submit(screen.getByRole('button',{name:'Save changes'}).closest('form')!));
  expect(post).toHaveBeenCalledWith(API.assetUpdate,expect.objectContaining({name:'ASSET-1',geo_node:'Branch A',asset_name:'Radio'}));
  expect(saved).toHaveBeenCalledWith('Asset updated.');
 });
});
