import { useFrappeGetCall } from "frappe-react-sdk";
import { Link, Navigate, useParams } from "react-router-dom";
import { API } from "../../lib/api";
import { formatDate } from "../../lib/format";
import { useSocietyBranding } from "../../ui/brand";
import { Icon } from "../../ui/icons";
import { MetricCard } from "../../ui/MetricCard";
import { isScheduledCommunication, useCommunicationHistory } from "./history";

const names:Record<string,string>={email:"Email",sms:"SMS",whatsapp:"WhatsApp",system:"In-app notifications"};
export default function ChannelOverview() {
 const {channel="email"}=useParams(),society=useSocietyBranding();
 const {rows:history,isLoading:historyLoading,error:historyError}=useCommunicationHistory(channel);
 const options=useFrappeGetCall<{message:{sender?:{name:string;email:string};channels:Record<string,boolean>;sms_templates?:unknown[]}}>(API.communicationOptions,undefined,"admin:communication_options");
 const gateway=useFrappeGetCall<{message:{name:string;phone_number:string;configured:boolean}}>(API.whatsappChannel,undefined,channel==="whatsapp"?"admin:wa:channel":null);
 const connection=useFrappeGetCall<{message:{connected:boolean}}>(API.whatsappConnection,undefined,channel==="whatsapp"?"admin:wa:connection":null);
 const optOuts=useFrappeGetCall<{message:{count:number;opt_outs:{name:string;phone_number:string;opted_out_on:string}[]}}>(API.whatsappOptOuts,undefined,channel==="whatsapp"?"admin:wa:optouts":null);
 if(!names[channel])return <Navigate to="/admin/communication/email/overview" replace />;
 if(historyError)return <p role="alert">Communication history could not be loaded. Reload to try again.</p>;
 if(historyLoading)return <p role="status">Loading communication history…</p>;
 const name=names[channel],base=`/admin/communication/${channel}`;
 const sent=history.filter(row=>["Sent","Queued","Partly Sent"].includes(row.status)).sort((a,b)=>b.date.localeCompare(a.date));
 const drafts=history.filter(row=>row.status==="Draft").sort((a,b)=>b.date.localeCompare(a.date));
 const scheduled=history.filter(isScheduledCommunication).sort((a,b)=>(a.scheduled_at||a.date).localeCompare(b.scheduled_at||b.date));
 const pending=history.filter(row=>row.status==="Pending approval").length;
 const delivered=history.reduce((sum,row)=>sum+(row.delivered||0),0),failed=history.reduce((sum,row)=>sum+(row.failed||0),0);
 const enabled=!!options.data?.message.channels[channel==="system"?"notification":channel];
 const status=channel==="whatsapp"?(connection.data?.message.connected?"Connected":"Not connected"):enabled?"Ready":"Unavailable";
 const latest=history.filter(row=>row.status!=="Draft").sort((a,b)=>b.date.localeCompare(a.date))[0];
 return <div className="channel-overview">
  <header className="channel-page-heading"><h1>{channel==="system"?name:`${name} channel`}</h1><Link className="channel-new-message" to={`${base}/compose`}><Icon.plus size={16}/>{channel==="email"?"New email":channel==="system"?"New notification":"New message"}</Link></header>
  <div className="channel-metrics">
   <MetricCard label="Channel status" value={<span className={`channel-ready ${enabled?"":"is-unavailable"}`}>{status}</span>} icon={channel==="email"?<Icon.mail size={19}/>:channel==="system"?<Icon.bell size={19}/>:channel==="whatsapp"?<Icon.whatsapp size={19}/>:<Icon.phone size={19}/>} note={channel==="email"?options.data?.message.sender?.email:channel==="whatsapp"?gateway.data?.message.phone_number:undefined}/>
   <MetricCard label="Messages delivered" value={delivered.toLocaleString()} icon={<Icon.check size={19}/>} note={`Across ${sent.length} sent messages`} />
   <MetricCard label="Awaiting approval" value={pending} icon={<Icon.hourglass size={19}/>} note={pending?"Pending campaigns":"No campaigns awaiting approval"} to={`${base}/sent?status=Pending+approval`} />
   <MetricCard label="Scheduled" value={scheduled.length} icon={<Icon.calendar size={19}/>} note="Upcoming messages" to={`${base}/sent?status=Scheduled`} />
   <MetricCard label="Drafts" value={drafts.length} icon={<Icon.file size={19}/>} note="Saved messages" to={`${base}/sent?status=Draft`} />
  </div>
  <div className="channel-overview-grid">
   <section className="channel-panel channel-sent"><header><h2>Sent messages</h2><Link to={`${base}/sent`}>View history <Icon.arrow size={13}/></Link></header>
    {sent.length?<div className="channel-table-scroll"><table><thead><tr>{["Message","Audience","Delivered","Sent on","Status"].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{sent.slice(0,8).map(row=><tr key={row.id}><td><Link to={`${base}/sent?message=${encodeURIComponent(row.id)}`}>{row.title}</Link><small>{row.branch}</small></td><td>{row.audience}</td><td>{row.delivered.toLocaleString()}<span> / {row.recipient_count.toLocaleString()}</span></td><td>{formatDate(row.date)}</td><td><span className="channel-sent-badge">{row.status}</span></td></tr>)}</tbody></table></div>:<div className="channel-empty"><Icon.send size={24}/><strong>No messages sent yet</strong><Link to={`${base}/compose`}>Create a message</Link></div>}
   </section>
   <aside className="channel-overview-aside">
    <section className="channel-panel"><header><h2>Channel details</h2></header><dl>
     <div><dt>Sender</dt><dd>{channel==="email"?options.data?.message.sender?.name:channel==="whatsapp"?gateway.data?.message.name:society?.name}</dd></div>
     {channel==="email"&&<div><dt>Email address</dt><dd>{options.data?.message.sender?.email}</dd></div>}
     {channel==="whatsapp"&&<div><dt>Phone number</dt><dd>{gateway.data?.message.phone_number}</dd></div>}
     <div><dt>Status</dt><dd>{status}</dd></div><div><dt>Last activity</dt><dd>{latest?formatDate(latest.date):"No activity yet"}</dd></div>
     {channel==="sms"&&<div><dt>Available templates</dt><dd>{options.data?.message.sms_templates?.length||0}</dd></div>}
    </dl>{channel==="whatsapp"&&<Link className="channel-settings-link" to={`${base}/channel`}>Channel settings <Icon.arrow size={13}/></Link>}</section>
    <section className="channel-panel"><header><h2>Delivery summary</h2></header><dl><div><dt>Delivered</dt><dd>{delivered.toLocaleString()}</dd></div><div><dt>Failed</dt><dd>{failed.toLocaleString()}</dd></div>{channel==="whatsapp"&&<div><dt>Opted out</dt><dd>{optOuts.data?.message.count||0}</dd></div>}</dl></section>
   </aside>
  </div>
  <section className="channel-panel channel-scheduled"><header><h2>Scheduled messages ({scheduled.length})</h2><Link to={`${base}/sent?status=Scheduled`}>View scheduled <Icon.arrow size={13}/></Link></header>{scheduled.length?<div>{scheduled.slice(0,3).map(row=><Link className="channel-draft-row" key={row.id} to={`${base}/sent?status=Scheduled&message=${encodeURIComponent(row.id)}`}><Icon.calendar size={16}/><span><strong>{row.title}</strong><small>{row.status === "Pending approval"?"Awaiting approval · ":""}{row.branch} · {row.audience}</small></span><time dateTime={row.scheduled_at}>{row.scheduled_at?new Date(row.scheduled_at).toLocaleString("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}):"Time not set"}</time><Icon.arrow size={14}/></Link>)}</div>:<div className="channel-empty compact"><Icon.calendar size={20}/><strong>No scheduled messages</strong></div>}</section>
  <section className="channel-panel channel-drafts"><header><h2>Saved drafts ({drafts.length})</h2><Link to={`${base}/sent?status=Draft`}>View drafts <Icon.arrow size={13}/></Link></header>{drafts.length?<div>{drafts.slice(0,3).map(row=><Link className="channel-draft-row" key={row.id} to={`${base}/sent?status=Draft&message=${encodeURIComponent(row.id)}`}><Icon.file size={16}/><span><strong>{row.title}</strong><small>{row.branch} · {row.audience}</small></span><time>{formatDate(row.date)}</time><Icon.arrow size={14}/></Link>)}</div>:<div className="channel-empty compact"><Icon.file size={20}/><strong>No saved drafts</strong></div>}</section>
 </div>;
}
