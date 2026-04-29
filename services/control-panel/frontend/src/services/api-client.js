import { TOKEN_KEY } from "../state/preferences.js";

export function getToken() {
  let token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    token = prompt("Enter control-panel token (viewer/operator/risk-manager/admin):", "admin-token") || "";
    token = token.trim();
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    }
  }
  return token;
}

export async function authedFetch(url, init = {}) {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  headers.set("X-Control-Panel-Token", token);
  return fetch(url, { ...init, headers });
}
