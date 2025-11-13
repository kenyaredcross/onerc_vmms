function sideBarApps() {
	return [
		{
			name: "learning",
			icon: "School",
			title: __("Learning"),
			route: "/lms",
		},
		{
			name: "frappe",
			icon: "Monitor",
			title: __("Desk"),
			route: "/app",
		},
		{
			name: "forum",
			icon: "MessageSquare",
			title: __("Forum"),
			route: "/raven",
		},
		{
			name: "helpdesk",
			icon: "HelpCircle",
			title: __("Help Desk"),
			route: "/helpdesk/my-tickets",
		},
	];
}

export { sideBarApps };
