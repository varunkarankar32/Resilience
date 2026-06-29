import { config } from "../config.js";

interface HttpErrorResponse {
  status: "error";
  message: string;
}

async function post<TBody, TResp>(
  path: string,
  body: TBody
): Promise<TResp> {
  const url = `${config.AGENT_ENGINE_URL}${path}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as HttpErrorResponse;
    throw new Error(
      `Agent engine request failed: ${response.status} ${errorData.message || response.statusText}`
    );
  }

  return (await response.json()) as TResp;
}

export const httpClient = Object.freeze({ post });
