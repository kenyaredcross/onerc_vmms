import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DeploymentPlace, DeploymentWhere } from '../portal/types';
import { DeploymentDestination } from './DeploymentDestination';

vi.mock('../portal/ui/OsmMap', () => ({
 OsmMap: ({ latitude, longitude, interactive }: { latitude: number; longitude: number; interactive: boolean }) =>
  <div data-testid="destination-map" data-lat={latitude} data-lon={longitude} data-interactive={String(interactive)} />,
}));
const place = (name: string, latitude: number | null, longitude: number | null): DeploymentPlace => ({
 name, address: `${name} address`, latitude, longitude, has_point: latitude !== null && longitude !== null,
 located_on: null, map: null, directions: null,
});
const where: DeploymentWhere = {
 site: place('Field hospital', -1.28, 36.82), meeting_point: place('Branch office', -1.3, 36.8),
 travel_notes: 'Report to reception before departure.', local_contact: { name: 'Asha Juma', phone: '+254700000000' },
};
describe('deployment destination', () => {
 it('starts with a fixed site preview and enables exploration only on request', async () => {
  render(<DeploymentDestination where={where} />);
  expect((await screen.findByTestId('destination-map')).dataset.interactive).toBe('false');
  expect(screen.getByRole('link', { name: /Get directions/ }).getAttribute('href')).toContain('-1.28');
  fireEvent.click(screen.getByRole('button', { name: /Explore map/ }));
  expect(screen.getByTestId('destination-map').dataset.interactive).toBe('true');
  fireEvent.click(screen.getByRole('button', { name: /Meeting point/ }));
  expect(screen.getByTestId('destination-map').dataset.lat).toBe('-1.3');
  expect(screen.getByTestId('destination-map').dataset.interactive).toBe('false');
  expect(screen.getByText(where.travel_notes!)).toBeTruthy();
 });
 it('keeps unlocated destinations visible without inventing a pin or directions', () => {
  render(<DeploymentDestination where={{ ...where, site: place('Field hospital', null, null), meeting_point: place('', null, null) }} />);
  expect(screen.getByText('Field hospital')).toBeTruthy();
  expect(screen.getByText(/Coordinates have not been added/)).toBeTruthy();
  expect(screen.queryByTestId('destination-map')).toBeNull();
  expect(screen.queryByRole('link', { name: /Get directions/ })).toBeNull();
 });
 it('labels branch fallback as approximate and rejects invalid coordinates', async () => {
  const { rerender } = render(<DeploymentDestination fallback={{ name: 'Nairobi branch', address: 'Branch address', latitude: -1.2, longitude: 36.8 }} />);
  expect(screen.getByText(/Branch reference/)).toBeTruthy();
  expect(screen.getByText(/Confirm the exact reporting point/)).toBeTruthy();
  expect(await screen.findByTestId('destination-map')).toBeTruthy();
  expect(screen.queryByRole('link', { name: /Get directions/ })).toBeNull();
  rerender(<DeploymentDestination where={{ ...where, site: place('Bad point', 100, 190), meeting_point: place('', null, null) }} />);
  expect(screen.queryByTestId('destination-map')).toBeNull();
 });
});
