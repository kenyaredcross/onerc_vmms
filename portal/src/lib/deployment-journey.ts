/** Mission status determines the illustration; it is not a live vehicle location. */
export function deploymentJourney(status: string) {
 if (status === 'Planned') return { position: 0, label: 'Not begun', point: 'start' } as const;
 if (status === 'Active' || status === 'Suspended') return { position: 50, label: status === 'Suspended' ? 'Paused' : 'Ongoing', point: 'middle' } as const;
 if (status === 'Completed' || status === 'Closed Out') return { position: 100, label: 'Completed', point: 'end' } as const;
 return { position: null, label: status || 'Status unavailable', point: null } as const;
}
