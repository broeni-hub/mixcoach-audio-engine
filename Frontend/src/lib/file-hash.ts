// Lightweight content fingerprint for audio files.
// Hashing 400MB end-to-end is slow, so we sample head + tail + size + name.
// This is deterministic for identical files and effectively collision-free
// for distinct audio uploads.

const SAMPLE_BYTES = 4 * 1024 * 1024; // 4 MiB head + 4 MiB tail

async function sha256Hex(buf: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function hashFile(file: File): Promise<string> {
  const size = file.size;
  const headEnd = Math.min(SAMPLE_BYTES, size);
  const tailStart = Math.max(headEnd, size - SAMPLE_BYTES);
  const head = await file.slice(0, headEnd).arrayBuffer();
  const tail = tailStart < size ? await file.slice(tailStart, size).arrayBuffer() : new ArrayBuffer(0);
  const meta = new TextEncoder().encode(`${file.name}|${size}|${file.type}`);
  const combined = new Uint8Array(head.byteLength + tail.byteLength + meta.byteLength);
  combined.set(new Uint8Array(head), 0);
  combined.set(new Uint8Array(tail), head.byteLength);
  combined.set(meta, head.byteLength + tail.byteLength);
  return sha256Hex(combined.buffer);
}

export async function hashFilesCombined(
  fileA: File,
  fileB?: File,
  extras?: Record<string, unknown>,
): Promise<string> {
  const a = await hashFile(fileA);
  const b = fileB ? await hashFile(fileB) : "";
  const extraStr = extras ? JSON.stringify(extras) : "";
  const buf = new TextEncoder().encode(`${a}|${b}|${extraStr}`);
  return sha256Hex(buf.buffer);
}

// ---- Hash → resultId cache (localStorage) -----------------------------------

const CACHE_KEY = "mixcoach.hashCache.v1";

type HashCache = Record<string, { resultId: string; at: number }>;

function readCache(): HashCache {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || "{}"); } catch { return {}; }
}

function writeCache(c: HashCache) {
  if (typeof window === "undefined") return;
  localStorage.setItem(CACHE_KEY, JSON.stringify(c));
}

export function getCachedResultId(hash: string): string | undefined {
  return readCache()[hash]?.resultId;
}

export function setCachedResultId(hash: string, resultId: string) {
  const c = readCache();
  c[hash] = { resultId, at: Date.now() };
  writeCache(c);
}

export function clearHashCache() {
  if (typeof window !== "undefined") localStorage.removeItem(CACHE_KEY);
}
