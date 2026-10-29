import { describe, expect, it } from 'vitest';
import { googleMapsUrl } from './maps';

describe('external Google Maps links', () => {
 it('opens the exact coordinate pair with a map pin', () => {
  const url = new URL(googleMapsUrl('-1.28,36.82'));
  expect(url.origin).toBe('https://www.google.com');
  expect(url.pathname).toBe('/maps/search/');
  expect(url.searchParams.get('api')).toBe('1');
  expect(url.searchParams.get('query')).toBe('-1.28,36.82');
 });
 it('preserves event venue addresses containing punctuation and non-ASCII characters', () => {
  const address = 'Centre A & B, Ng’ong Road #2, Nairobi';
  expect(new URL(googleMapsUrl(address)).searchParams.get('query')).toBe(address);
 });
 it('requests directions without inventing a starting location', () => {
  const url = new URL(googleMapsUrl('0,36.82', 'directions'));
  expect(url.pathname).toBe('/maps/dir/');
  expect(url.searchParams.get('destination')).toBe('0,36.82');
  expect(url.searchParams.has('origin')).toBe(false);
 });
});
