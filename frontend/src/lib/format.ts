export function formatDate(dateString: string, month: "short" | "long" = "short"): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month,
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Format seconds as m:ss. */
export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Keep in sync with ALLOWED_AUDIO_EXTENSIONS in backend/app/main.py.
export const AUDIO_EXTENSIONS = [
  ".aac", ".flac", ".m4a", ".mp3", ".mp4", ".mpeg", ".mpga", ".oga",
  ".ogg", ".opus", ".wav", ".webm", ".wma",
];

export function isAudioFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return file.type.startsWith("audio/") || AUDIO_EXTENSIONS.some((ext) => name.endsWith(ext));
}
