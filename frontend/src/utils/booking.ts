import { ref } from "vue";

const _attendeesState = ref<Attendee[]>([]);

interface Attendee {
  full_name: string;
  email: string;
  phone: string;
}
export class AttendeeBooking {
  private SESSION_KEY = "attendee_booking";

  constructor() {
    this.loadFromSession();
  }

  private loadFromSession() {
    const data = sessionStorage.getItem(this.SESSION_KEY);
    _attendeesState.value = data ? JSON.parse(data) : [];
  }

  saveAttendees(attendees: Attendee[]) {
    sessionStorage.setItem(this.SESSION_KEY, JSON.stringify(attendees));
    this.loadFromSession();
  }
  getAttendees(): Attendee[] {
    return _attendeesState.value;
  }

  clearAttendees() {
    sessionStorage.removeItem(this.SESSION_KEY);
    this.loadFromSession();
  }
}
export const attendeeBooking = new AttendeeBooking();
