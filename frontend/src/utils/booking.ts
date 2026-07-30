import { ref } from "vue";

interface TicketDetails {
  ticket_type: string;
  number_of_tickets: number;
  total_price: number;
}
interface Attendee {
  full_name: string;
  email: string;
  phone: string;
}

const _bookingDetails = ref<BookingData>({} as BookingData);

interface BookingData {
  ticketDetails: TicketDetails;
  attendees: Attendee[];
}
export class AttendeeBooking {
  private ATTENDEE_SESSION_KEY = "attendee_booking";
  private TICKET_SESSION_KEY = "ticket_details";

  constructor() {
    this.bookingData();
  }

  set attendees(attendees: Attendee[]) {
    sessionStorage.setItem(
      this.ATTENDEE_SESSION_KEY,
      JSON.stringify(attendees),
    );
    this.bookingData();
  }
  get attendees(): Attendee[] {
    return sessionStorage.getItem(this.ATTENDEE_SESSION_KEY)
      ? JSON.parse(sessionStorage.getItem(this.ATTENDEE_SESSION_KEY)!)
      : [];
  }

  clearAttendees() {
    sessionStorage.removeItem(this.ATTENDEE_SESSION_KEY);
  }

  set TicketDetails(details: TicketDetails) {
    sessionStorage.setItem(this.TICKET_SESSION_KEY, JSON.stringify(details));
    this.bookingData();
  }

  get TicketDetails(): TicketDetails {
    const data = sessionStorage.getItem(this.TICKET_SESSION_KEY) ?? "";
    return data ? JSON.parse(data) : ({} as TicketDetails);
  }

  clearTicketDetails() {
    sessionStorage.removeItem(this.TICKET_SESSION_KEY);
  }

  clearBookingData() {
    this.clearAttendees();
    this.clearTicketDetails();
    _bookingDetails.value = {} as BookingData;
  }

  private bookingData() {
    const bookingData: BookingData = {
      ticketDetails: this.TicketDetails,
      attendees: this.attendees,
    };
    _bookingDetails.value = bookingData ? bookingData : ({} as BookingData);
  }

  getBookingData(): BookingData {
    return _bookingDetails.value;
  }
}
export const attendeeBooking = new AttendeeBooking();
