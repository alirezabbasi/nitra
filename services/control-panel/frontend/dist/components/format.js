export function tableSlice(rows, limit = 30) {
  return (rows || []).slice(0, limit);
}

export function fmt(value) {
  if (typeof value === "number" && Math.abs(value) >= 1000) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value ?? "-");
}
