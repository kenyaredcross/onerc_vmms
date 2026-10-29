import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OsmMap } from './OsmMap';

describe('embedded map external destination', () => {
 it('makes the fixed preview a Google Maps link at the same coordinates', () => {
  render(<OsmMap latitude={-1.28} longitude={36.82} label="Deployment site" interactive={false} />);
  const link = screen.getByRole('link', { name: 'Open in Google Maps ↗' });
  const url = new URL(link.getAttribute('href')!);
  expect(url.hostname).toBe('www.google.com');
  expect(url.searchParams.get('query')).toBe('-1.28,36.82');
  expect(link.className).toContain('inset-0');
  expect(link.getAttribute('target')).toBe('_blank');
  expect(screen.getByText('OpenStreetMap').closest('a')?.getAttribute('href')).toBe('https://www.openstreetmap.org/copyright');
 });
 it('keeps exploration controls available when the map is interactive', () => {
  render(<OsmMap latitude={0} longitude={36.82} interactive />);
  expect(screen.getByRole('button', { name: 'Zoom in' })).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Open in Google Maps ↗' }).className).not.toContain('inset-0');
 });
});
