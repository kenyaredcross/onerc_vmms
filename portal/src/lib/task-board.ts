export const taskStages = [
 { key: "assigned", label: "Assigned" },
 { key: "accepted", label: "Accepted" },
 { key: "progress", label: "In progress" },
 { key: "submitted", label: "Awaiting review" },
 { key: "completed", label: "Completed" },
 { key: "closed", label: "Closed" },
];
export function taskStage(task: { status: string; percent_complete: number; board_stage?: string }) {
 if (task.status === "accepted" && (task.board_stage === "progress" || task.percent_complete > 0)) return "progress";
 return ["cancelled", "declined", "reassigned"].includes(task.status) ? "closed" : task.status;
}
const moves: Record<string,string[]> = {
 assigned: ["accepted", "progress", "closed"],
 accepted: ["progress", "submitted", "closed"],
 progress: ["submitted", "closed"],
 submitted: ["progress", "completed", "closed"],
 completed: [],
 closed: [],
};
export function availableTaskMoves(task: Parameters<typeof taskStage>[0]) {
 return moves[taskStage(task)] || [];
}
