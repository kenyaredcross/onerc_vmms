export function* generateTimeOptions(intervalMinutes: number = 30) {
  for (let hour = 0; hour < 24; hour++) {
    for (let minute = 0; minute < 60; minute += intervalMinutes) {
      const timeValue = `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`;
      const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
      const period = hour < 12 ? "AM" : "PM";
      const minuteStr = minute === 0 ? "00" : minute.toString();
      const timeLabel = `${displayHour}:${minuteStr} ${period}`;

      yield { value: timeValue, label: timeLabel };
    }
  }
}