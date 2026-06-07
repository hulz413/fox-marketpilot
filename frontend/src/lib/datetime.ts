function getLocalDateParts(value: string) {
  const date = new Date(value);
  const pad = (part: number) => String(part).padStart(2, "0");

  return {
    year: String(date.getFullYear()),
    month: pad(date.getMonth() + 1),
    day: pad(date.getDate()),
    hour: pad(date.getHours()),
    minute: pad(date.getMinutes()),
    second: pad(date.getSeconds()),
  };
}

export function formatDate(value: string) {
  const { year, month, day } = getLocalDateParts(value);

  return `${year}-${month}-${day}`;
}

export function formatDateTime(value: string) {
  const { year, month, day, hour, minute, second } = getLocalDateParts(value);

  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}
