import { NextRequest } from "next/server";

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

type StreamingRequestInit = RequestInit & { duplex?: "half" };

const INTERNAL_API_URL = (
  process.env.INTERNAL_API_URL || "http://backend-api:8000"
).replace(/\/$/, "");

const PROHIBITED_PROXY_HEADERS = [
  "connection",
  "content-length",
  "expect",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "proxy-connection",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
];

function stripProhibitedProxyHeaders(headers: Headers) {
  const connectionTokens = headers.get("connection")?.split(",") || [];
  for (const token of connectionTokens) {
    const header = token.trim();
    if (header) headers.delete(header);
  }
  for (const header of PROHIBITED_PROXY_HEADERS) {
    headers.delete(header);
  }
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(`${INTERNAL_API_URL}/${path.join("/")}`);
  targetUrl.search = incomingUrl.search;

  const headers = new Headers(request.headers);
  stripProhibitedProxyHeaders(headers);

  const apiKey = process.env.API_KEY;
  if (apiKey) {
    headers.set("x-api-key", apiKey);
  }

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const requestInit: StreamingRequestInit = {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    redirect: "manual",
    cache: "no-store",
  };
  if (hasBody) {
    requestInit.duplex = "half";
  }

  const response = await fetch(targetUrl, requestInit);
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  stripProhibitedProxyHeaders(responseHeaders);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
