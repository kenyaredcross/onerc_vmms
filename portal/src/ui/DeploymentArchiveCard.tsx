import { Link } from 'react-router-dom';
import { formatDate, geoPath } from '../lib/format';
import type { DeploymentSummary, DeploymentWhere } from '../portal/types';
import { Icon } from './icons';
import { DeploymentJourney } from './DeploymentJourney';

/** A mission keeps its actual status; completion never implies verified hours. */
export function DeploymentArchiveCard({ row, to }: {
 row: DeploymentSummary & { title?: string; where?: DeploymentWhere | null }; to: string;
}) {
 const filed = row.closed_out_on || row.actual_end || row.end_date;
 const year = filed ? filed.slice(0, 4) : null;
 const finished = ['Completed', 'Closed Out'].includes(row.status);
 const destination = row.where?.site.name || row.where?.site.address || geoPath(row.geo_path) || 'Location not recorded';
 return <Link to={to} className="deployment-archive-card">
  <div className="deployment-archive-top"><span>{row.name}</span><span className={`deployment-archive-status ${finished ? 'is-complete' : ''}`}><span aria-hidden="true" />{row.status}</span></div>
  <h3>{row.title || row.terms_of_reference || row.name}</h3>
  <DeploymentJourney status={row.status} origin={row.where?.meeting_point.name || row.where?.meeting_point.address || 'Meeting point to be confirmed'} destination={destination} />
  <div className="deployment-archive-bottom"><span><small>{row.status === 'Planned' ? 'Starts' : 'Deployed'}</small><strong>{row.start_date ? formatDate(row.start_date) : 'Start date not recorded'}</strong></span><span><small>{row.closed_out_on ? 'Closed out' : row.status === 'Cancelled' ? 'End date' : finished ? 'Ended' : 'Expected end'}</small><strong>{filed ? formatDate(filed) : 'Date not recorded'}</strong></span></div>
  <div className="deployment-archive-foot"><span>{year ? `${year} mission file` : 'Mission file'}</span><span>View record <Icon.arrow size={12} /></span></div>
 </Link>;
}
