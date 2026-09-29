import { MeetingStatus } from "@/lib/api";

const STYLES: Record<MeetingStatus, { label: string; className: string }> = {
  queued: { label: "Queued", className: "bg-gray-100 text-gray-700" },
  processing: { label: "Processing", className: "bg-amber-100 text-amber-800" },
  completed: { label: "Completed", className: "bg-green-100 text-green-800" },
  failed: { label: "Failed", className: "bg-red-100 text-red-800" },
};

export default function StatusBadge({ status }: { status: MeetingStatus }) {
  const { label, className } = STYLES[status] ?? STYLES.completed;
  const pending = status === "queued" || status === "processing";

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded ${className}`}
    >
      {pending && (
        <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" aria-hidden="true" />
      )}
      {label}
    </span>
  );
}
