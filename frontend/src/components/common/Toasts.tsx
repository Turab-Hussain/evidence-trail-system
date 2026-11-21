export interface Toast {
  id: number;
  message: string;
  kind: "info" | "error";
}

/** Short confirmations and errors. Announced politely to screen readers. */
export function Toasts({ toasts }: { toasts: Toast[] }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.kind === "error" ? "toast-error" : ""}`}>
          {toast.message}
        </div>
      ))}
    </div>
  );
}
