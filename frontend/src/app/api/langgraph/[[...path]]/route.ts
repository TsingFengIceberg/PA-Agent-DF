import { type NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const GATEWAY_BASE_URL =
  process.env.DEER_FLOW_INTERNAL_GATEWAY_BASE_URL ?? "http://127.0.0.1:8001";

const HOP_BY_HOP_HEADERS = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
] as const;

function buildGatewayUrl(path: string[] | undefined, search: string) {
  const pathname = ["api", ...(path ?? []).map(encodeURIComponent)].join("/");
  return `${GATEWAY_BASE_URL.replace(/\/+$/, "")}/${pathname}${search}`;
}

function buildHeaders(request: NextRequest) {
  const headers = new Headers(request.headers);
  for (const name of ["host", "content-length", ...HOP_BY_HOP_HEADERS]) {
    headers.delete(name);
  }
  headers.set("accept-encoding", "identity");
  return headers;
}

async function proxyRequest(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await context.params;
  const target = buildGatewayUrl(path, request.nextUrl.search);
  const method = request.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";
  const init: RequestInit & { duplex?: "half" } = {
    method,
    headers: buildHeaders(request),
    redirect: "manual",
    cache: "no-store",
    signal: request.signal,
  };

  if (hasBody) {
    init.body = request.body;
    init.duplex = "half";
  }

  const upstream = await fetch(target, init);
  const headers = new Headers(upstream.headers);
  for (const name of ["content-length", ...HOP_BY_HOP_HEADERS]) {
    headers.delete(name);
  }
  const cacheControl = headers.get("Cache-Control");
  headers.set(
    "Cache-Control",
    cacheControl ? `${cacheControl}, no-transform` : "no-cache, no-transform",
  );
  headers.set("X-Accel-Buffering", "no");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
