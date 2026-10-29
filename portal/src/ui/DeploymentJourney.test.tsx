import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DeploymentJourney } from './DeploymentJourney';

describe('deployment journey indicator', () => {
 it.each([['Planned','start','0%'],['Active','middle','50%'],['Suspended','middle','50%'],['Completed','end','100%'],['Closed Out','end','100%']])('places %s at the %s of the journey', (status, position, left) => {
  render(<DeploymentJourney status={status} origin="Branch office" destination="Field hospital" />);
  expect(screen.getByRole('img', { name: /Mission position/ }).getAttribute('data-position')).toBe(position);
  expect(screen.getByRole('img', { name: /Mission position/ }).style.left).toBe(left);
  expect(screen.getByText('Branch office')).toBeTruthy();
  expect(screen.getByText('Field hospital')).toBeTruthy();
 });
 it('does not show a cancelled mission as having arrived', () => {
  render(<DeploymentJourney status="Cancelled" origin="Branch office" destination="Field hospital" />);
  expect(screen.queryByRole('img', { name: /Mission position/ })).toBeNull();
  expect(screen.getByText('Cancelled')).toBeTruthy();
 });
});
