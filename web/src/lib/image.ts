// Downscale a photo before upload. Anthropic vision re-downscales to ~1568px long edge anyway,
// and OpenRouter caps the request payload at 32 MB — so sending a full phone photo wastes
// bandwidth, cost, and R2 storage with zero analysis benefit. 2048px keeps a quality archive
// for progress photos / ghost-overlay while staying ~0.5-1.5 MB. Falls back to the original
// file if the browser can't decode it (e.g. some HEIC) — the API still magic-byte-validates.
export async function downscaleImage(
  file: File,
  maxEdge = 2048,
  quality = 0.9,
): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file);
    const { width, height } = bitmap;
    const longest = Math.max(width, height);
    if (longest <= maxEdge) {
      bitmap.close();
      return file; // already small enough — keep original bytes
    }
    const scale = maxEdge / longest;
    const w = Math.round(width * scale);
    const h = Math.round(height * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", quality),
    );
    if (!blob) return file;
    const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg" });
  } catch {
    return file; // undecodable format — let the API validate the original
  }
}
