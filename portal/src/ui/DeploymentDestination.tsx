import { googleMapsUrl } from "../lib/maps";
import { lazy, Suspense, useMemo, useState } from 'react';
import type { DeploymentPlace, DeploymentWhere } from '../portal/types';
import { deploymentJourney } from '../lib/deployment-journey';
import type { MapJourney } from '../portal/ui/OsmMap';
import { Icon } from './icons';

const OsmMap = lazy(() => import('../portal/ui/OsmMap').then(module => ({ default: module.OsmMap })));
type ReferencePoint = { name: string; address: string | null; latitude: number; longitude: number };
function located(point: Partial<DeploymentPlace> | undefined): point is DeploymentPlace & { latitude: number; longitude: number } {
 return !!point?.has_point && typeof point.latitude === 'number' && Number.isFinite(point.latitude) && Math.abs(point.latitude) <= 90
  && typeof point.longitude === 'number' && Number.isFinite(point.longitude) && Math.abs(point.longitude) <= 180;
}

/** Destination details come only from the deployment; a branch is explicitly approximate. */
export function DeploymentDestination({ where, fallback, area, status = '', mapOnly = false }: {
 where?: DeploymentWhere | null; fallback?: ReferencePoint | null; area?: string; status?: string; mapOnly?: boolean;
}) {
 const [selection, setSelection] = useState('');
 const [interactive, setInteractive] = useState(false);
 const journey = useMemo<MapJourney | undefined>(() => {
  const start = where?.meeting_point, end = where?.site;
  if (!located(start) || !located(end) || (start.latitude === end.latitude && start.longitude === end.longitude)) return undefined;
  return { start: { ...start, label: start.name || start.address || 'Meeting point' }, end: { ...end, label: end.name || end.address || 'Deployment site' }, position: deploymentJourney(status).position, status };
 }, [where, status]);
 const places = [
  { key: 'site', label: 'Deployment site', point: where?.site },
  { key: 'meeting', label: 'Meeting point', point: where?.meeting_point },
 ].filter(item => item.point && (item.point.name || item.point.address || located(item.point)));
 const reference = !places.length && fallback ? { key: 'branch', label: 'Branch reference', point: { ...fallback, has_point: true } } : null;
 const choices = places.length ? places : reference ? [reference] : [];
 const current = choices.find(item => item.key === selection) || choices.find(item => located(item.point)) || choices[0];
 const point = current?.point;
 const hasPoint = located(point);
 const choose = (key: string) => { setSelection(key); setInteractive(false); };
 const directions = hasPoint && current?.key !== 'branch'
  ? googleMapsUrl(`${point.latitude},${point.longitude}`, 'directions') : null;
 return <section className={`deployment-destination${mapOnly ? ' deployment-destination-map-only' : ''}`} aria-label="Deployment destination">
  <div className="deployment-destination-info">
   <span className="deployment-destination-eyebrow"><Icon.pin size={14} /> Deployment destination</span>
   <h2>Know where you’re going</h2>
   {area && <p className="deployment-destination-area">{area}</p>}
   {choices.length > 0 && <div className="deployment-place-switch" role="group" aria-label="Choose location">
    {choices.map(item => <button type="button" key={item.key} aria-pressed={current?.key === item.key} onClick={() => choose(item.key)}>{item.label}</button>)}
   </div>}
   <div className="deployment-destination-address" aria-live="polite">
    <h3>{point?.name || point?.address || 'Location to be confirmed'}</h3>
    {point?.name && point.address && <p>{point.address}</p>}
    {current?.key === 'branch' && <p>Approximate branch reference. Confirm the exact reporting point with your coordinator.</p>}
   </div>
   {where?.local_contact.name && <div className="deployment-destination-contact"><Icon.user size={15} /><span><small>Local contact</small><strong>{where.local_contact.name}</strong>{where.local_contact.phone && <a href={`tel:${where.local_contact.phone}`}>{where.local_contact.phone}</a>}</span></div>}
   {where?.travel_notes && <div className="deployment-travel-note"><strong>Before you travel</strong><p>{where.travel_notes}</p></div>}
   {directions && <a className="deployment-directions" href={directions} target="_blank" rel="noreferrer"><Icon.external size={14} />Get directions</a>}
  </div>
  <div className="deployment-destination-map">
   {hasPoint ? <>
    <Suspense fallback={<div className="deployment-map-empty">Loading destination map…</div>}>
     <OsmMap latitude={point.latitude} longitude={point.longitude} label={point.name || point.address || current?.label} height={360} zoom={13} interactive={interactive} journey={journey} className="deployment-map-canvas" />
    </Suspense>
    <div className="deployment-map-caption"><span><span className="deployment-map-dot" />{journey ? `Mission status · ${deploymentJourney(status).label}` : interactive ? 'Explore the area' : 'Destination preview'}</span><button type="button" aria-pressed={interactive} onClick={() => setInteractive(value => !value)}>{interactive ? 'Keep map fixed' : 'Explore map'}<Icon.arrow size={14} /></button></div>
   </> : <div className="deployment-map-empty"><Icon.pin size={28} /><strong>Location to be confirmed</strong><p>Coordinates have not been added for this location. Ask your coordinator to confirm the reporting point before travelling.</p></div>}
  </div>
 </section>;
}
