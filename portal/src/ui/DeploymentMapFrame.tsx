import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

/** A single map moves from the document header to the mission-record sidebar. */
export function DeploymentMapFrame({ card, map, dockTarget }: {
 card: ReactNode; map: ReactNode; dockTarget: HTMLDivElement | null;
}) {
 const hero = useRef<HTMLDivElement>(null);
 const [largeTarget, setLargeTarget] = useState<HTMLDivElement | null>(null);
 const [docked, setDocked] = useState(false);
 useEffect(() => {
  const media = window.matchMedia('(min-width: 1024px)');
  if (!hero.current || !('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver(([entry]) => {
   setDocked(media.matches && entry.boundingClientRect.top < 72 && entry.intersectionRatio < .5);
  }, { rootMargin: '-72px 0px 0px 0px', threshold: [0, .5, 1] });
  observer.observe(hero.current);
  const resize = () => { if (!media.matches) setDocked(false); };
  media.addEventListener('change', resize);
  return () => { observer.disconnect(); media.removeEventListener('change', resize); };
 }, []);
 const compact = docked && !!dockTarget;
 const target = compact ? dockTarget : largeTarget;
 return <>
  <div ref={hero} className="deployment-document-hero">
   <div className="deployment-document-card">{card}</div>
   <div ref={setLargeTarget} className="deployment-document-map-slot" />
  </div>
  {target && createPortal(<div className={compact ? 'deployment-document-map is-compact' : 'deployment-document-map'}>{map}</div>, target)}
 </>;
}
