import { useState, type ReactNode } from "react";
import { Icon } from "../../ui/icons";
import { Button } from "../../ui/primitives";
export function MessageComposer({
	channel,
	title,
	body,
	onTitle,
	onBody,
	audience,
	recipients,
	settings,
	ready,
	canSend,
	onReview,
	onSaveDraft,
	status,
	templates,
	onTemplate,
}: {
	channel: string;
	title: string;
	body: string;
	onTitle: (value: string) => void;
	onBody: (value: string) => void;
	audience: string;
	recipients: ReactNode;
	settings: ReactNode;
	ready: boolean;
	canSend: boolean;
	onReview: () => void;
	onSaveDraft: () => void;
	status: ReactNode;
	templates?: Array<{ name: string; template_name: string; message: string }>;
	onTemplate?: (name: string) => void;
}) {
	const [preview, setPreview] = useState(false);
 const [recipientOpen,setRecipientOpen]=useState(!audience);
	const campaign = channel === "sms" || channel === "whatsapp";
	const unicode = /[^\u0000-\u007f]/.test(body);
	const single = unicode ? 70 : 160;
	const multipart = unicode ? 67 : 153;
	const segments = body.length <= single ? (body.length ? 1 : 0) : Math.ceil(body.length / multipart);
	return (
		<div className="comm-compose">
			{status}
			<details className="comm-recipient-picker" open={recipientOpen} onToggle={e=>setRecipientOpen(e.currentTarget.open)}>
				<summary>
					<span>To</span>
					<strong>{audience || "Select recipients"}</strong>
					<Icon.chevron size={14} />
				</summary>
				<div className="comm-recipient-fields">{recipients}</div>
			</details>
			<label className="comm-subject">
				<span>{campaign ? "Campaign" : "Subject"}</span>
				<input
					aria-label={campaign ? "Campaign name" : "Subject"}
					value={title}
					onChange={(e) => onTitle(e.target.value)}
					placeholder={campaign ? "Name this campaign" : "Add a subject"}
				/>
			</label>
			{channel === "sms" && !!templates?.length && (
				<label className="comm-template">
					<span>Template</span>
					<select aria-label="SMS template" onChange={(e) => onTemplate?.(e.target.value)} defaultValue="">
						<option value="">Start from a template</option>
						{templates.map((item) => (
							<option key={item.name} value={item.name}>
								{item.template_name}
							</option>
						))}
					</select>
				</label>
			)}
			<div className="comm-compose-body">
				{preview ? (
					<article className={`comm-compose-preview ${campaign ? "is-chat-preview" : ""}`}>
						<h2>{title || "Subject"}</h2>
						<p>{body || "Your message preview will appear here."}</p>
						{channel === "whatsapp" && <small>Reply STOP to stop receiving messages from us.</small>}
					</article>
				) : (
					<textarea
						aria-label="Message body"
						placeholder={channel === "sms" ? "Write your SMS…" : "Write your message…"}
						value={body}
						onChange={(e) => onBody(e.target.value)}
					/>
				)}
			</div>
			<details className="comm-compose-settings">
				<summary>
					<Icon.filter size={15} />
					Message settings
					<Icon.chevron size={14} />
				</summary>
				<div>{settings}</div>
			</details>
			<footer className="comm-compose-footer">
				<div className="flex flex-wrap items-center gap-3">
					<button
						className="comm-preview-button"
						type="button"
						onClick={() => setPreview(!preview)}
						aria-pressed={preview}
					>
						{preview ? "Edit message" : "Preview"}
					</button>
					{channel === "sms" && (
						<span>
							{body.length} characters · {segments} SMS {segments === 1 ? "segment" : "segments"}
						</span>
					)}
				</div>
				<div className="flex flex-wrap items-center gap-2">
					<button type="button" className="comm-save-draft" onClick={onSaveDraft}>
						Save draft
					</button>
					<Button variant="primary" disabled={!ready || !canSend} onClick={onReview}>
						<Icon.send size={14} />
						{campaign ? "Create campaign draft" : "Review & send"}
					</Button>
				</div>
			</footer>
			{!canSend && <p className="comm-permission-note">You have read-only access to this channel.</p>}
		</div>
	);
}
