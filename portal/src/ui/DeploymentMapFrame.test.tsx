import { useState } from 'react';
import { act, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { DeploymentMapFrame } from './DeploymentMapFrame';
let observe: IntersectionObserverCallback;
function Screen() {
 const [target, setTarget] = useState<HTMLDivElement | null>(null);
 return <><DeploymentMapFrame card={<div>Deployment card</div>} map={<div role="img" aria-label="Mission map" />} dockTarget={target} /><aside><div data-testid="map-dock" ref={setTarget} /><h2>Mission record</h2></aside></>;
}
afterEach(() => vi.unstubAllGlobals());
it('moves one map above the mission record on scroll and restores it at the top', () => {
 vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener() {}, removeEventListener() {} }));
 vi.stubGlobal('IntersectionObserver', class { constructor(callback: IntersectionObserverCallback) { observe=callback; } observe() {} disconnect() {} });
 render(<Screen />);
 expect(screen.getAllByRole('img', {name:'Mission map'})).toHaveLength(1);
 expect(screen.getByTestId('map-dock').children.length).toBe(0);
 act(() => observe([{ intersectionRatio:0, boundingClientRect:{top:-500} } as IntersectionObserverEntry], {} as IntersectionObserver));
 expect(screen.getByTestId('map-dock').contains(screen.getByRole('img', {name:'Mission map'}))).toBe(true);
 expect(screen.getAllByRole('img', {name:'Mission map'})).toHaveLength(1);
 act(() => observe([{ intersectionRatio:1, boundingClientRect:{top:100} } as IntersectionObserverEntry], {} as IntersectionObserver));
 expect(screen.getByTestId('map-dock').children.length).toBe(0);
 expect(screen.getByText('Deployment card')).toBeTruthy();
});
