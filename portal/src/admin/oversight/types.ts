/** What `vmmsx/api/oversight.py` sends. One row per county, or per region. */
export interface AreaRow {
	name: string;
	label: string;
	code: string | null;
	parent: string | null;
	volunteers: number;
	members: number;
	new_30d: number;
	expiring_60d: number;
	waiting: number;
	waiting_late: number;
	with_applicant: number;
	deployments: number;
	materials_items: number;
	materials_total: number;
	materials_lent: number;
	oldest_days: number;
	has_approver?: boolean;
	without_approver?: number;
	/** On the national tab: the counties a region row is made of. */
	counties?: string[];
}

export interface Place {
	name: string;
	label: string;
	level?: string;
	code?: string | null;
}

export interface Count {
	label: string;
	count: number;
}

export interface People {
	total: number;
	gender: Count[];
	age: Count[];
	disability: Count[];
}

export interface Overview {
	as_of: string;
	area: Place | null;
	units: AreaRow[];
	rows: AreaRow[];
	totals: AreaRow;
	selected: Place | null;
	selected_totals: AreaRow | null;
	breakdown: {
		volunteers: People;
		members: People;
		plans: Count[];
		materials: Array<{ category: string; items: number; total: number; lent: number }>;
		trend: Array<{ month: string; volunteers: number; members: number }>;
	};
	attention: {
		mine: number;
		late: Array<{ name: string; label: string; count: number; oldest_days: number }>;
		without_approver: Place[];
		without_head: Place[];
		lent_out: number;
	};
	/** The region tab only: the areas this person may switch between. */
	areas?: Place[];
}

export interface MapShapes {
	view_box: string;
	shapes: Array<{ name: string; path: string | null; centre: [number, number] }>;
	has_file: boolean;
	matched: number;
	credit: string | null;
}
