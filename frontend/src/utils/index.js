export function getSidebarLinks() {
  return [
    {
      label: "Dashboard",
      icon: "LayoutDashboard",
      to: "Dashboard",
      activeFor: ["Dashboard"],
    },
    {
      label: "Opportunities",
      icon: "Briefcase",
      to: "Jobs",
      activeFor: ["Jobs", "JobDetail", "NewJobApplication"],
    },
    {
      label: "Events",
      icon: "Calendar",
      to: "Events",
      activeFor: ["Events"],
    },
    {
      label: "Membership",
      icon: "Users",
      to: "Membership",
      activeFor: ["Membership"],
    },
    {
      label: "Learning",
      icon: "BookOpen",
      to: "lms",
    },
  ];
}

export function convertToTitleCase(str) {
  if (!str) {
    return "";
  }

  return str
    .toLowerCase()
    .split(" ")
    .map(function (word) {
      return word.charAt(0).toUpperCase().concat(word.substr(1));
    })
    .join(" ");
}
