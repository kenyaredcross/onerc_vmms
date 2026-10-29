import { deploymentJourney } from '../lib/deployment-journey';
import { Icon } from './icons';

export function DeploymentJourney({ status, origin, destination }: { status: string; origin: string; destination: string }) {
 const journey = deploymentJourney(status);
 return <div className="deployment-journey">
  <div className="deployment-journey-places">
   <span><small>Meeting point</small><strong title={origin}>{origin}</strong></span>
   <span><small>Deployment site</small><strong title={destination}>{destination}</strong></span>
  </div>
  <div className="deployment-journey-track">
   <span className="deployment-journey-line" aria-hidden="true" />
   <span className="deployment-journey-dot is-start" aria-hidden="true" />
   <span className="deployment-journey-dot is-end" aria-hidden="true" />
   {journey.position !== null && <span className="deployment-journey-vehicle" role="img" aria-label={`Mission position: ${journey.label}`} data-position={journey.point} style={{ left: `${journey.position}%` }}><Icon.truck size={19} /></span>}
  </div>
  <small className="deployment-journey-caption">{journey.label}</small>
 </div>;
}
