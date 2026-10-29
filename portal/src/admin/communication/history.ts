import type { GeoNode } from "../../portal/types";
import { useContext, useEffect } from "react";
import { FrappeContext, useFrappeGetCall } from "frappe-react-sdk";
import { API } from "../../lib/api";
export interface DraftSettings {
	urgency: string;
	summary: string;
	expiresOn: string;
	linkLabel: string;
	linkHref: string;
	announcementType: string;
	smsTemplate: string;
	delivery: "approval" | "scheduled";
	scheduledAt: string;
	smsSourceType: string;
	smsSourceDoctype: string;
	smsPhoneField: string;
	smsFilters: Array<{ filter_field: string; operator: string; filter_value: string }>;
	smsCsvFile: string;
	smsPhoneNumbers: string;
}
export interface CommunicationRecord {
	id: string;
	channel: string;
	title: string;
	body: string;
	status: string;
	date: string;
	sender: string;
	sender_email: string;
	audience: string;
	branch: string;
	recipient_count: number;
	delivered: number;
	failed: number;
	opened: number;
	attachments?: Array<{name:string;url:string;size:string}>;
 scheduled_at?: string;
	pinned?: boolean;
	chain?: GeoNode[];
	who?: string;
	draft_fields?: DraftSettings;
	recipients: Array<{ name: string; address: string; status: string }>;
}
/** Server-backed history and drafts share the existing session and geo permissions. */
const changed = "vmms:communication-changed";
export const notifyCommunicationChanged=()=>window.dispatchEvent(new Event(changed));
export function useCommunicationHistory(channel: string) {
 const result = useFrappeGetCall<{message: CommunicationRecord[]}>(API.communicationHistory, {channel}, `communication:history:${channel}`, {refreshInterval: 30000});
 useEffect(() => { const refresh=()=>void result.mutate(); window.addEventListener(changed,refresh);return ()=>window.removeEventListener(changed,refresh); },[result.mutate]);
 return {rows:result.data?.message ?? [],isLoading:result.isLoading,error:result.error};
}
export function useCommunicationActions() {
 const {call}=useContext(FrappeContext)!;
 return {
  saveCommunicationDraft: async(data: Record<string,unknown>) => {const result=await call.post<{message:CommunicationRecord}>(API.communicationDraft,{data});window.dispatchEvent(new Event(changed));return result.message;},
  pinCommunication: async(id:string) => {await call.post(API.communicationPin,{id});window.dispatchEvent(new Event(changed));},
 };
}

export function isScheduledCommunication(row: CommunicationRecord) {
 return row.status === "Scheduled" || (!!row.scheduled_at && !["Draft","Sent","Failed","Cancelled"].includes(row.status));
}
