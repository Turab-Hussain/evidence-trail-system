import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { Toasts, type Toast } from "../components/common/Toasts";

type Notify = (message: string, kind?: Toast["kind"]) => void;

const ToastContext = createContext<Notify | null>(null);

/** Provides ``useNotify()`` and renders the toast stack once for the whole app. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const notify = useCallback<Notify>((message, kind = "info") => {
    const id = nextId.current++;
    setToasts((current) => [...current, { id, message, kind }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4500);
  }, []);

  const value = useMemo(() => notify, [notify]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toasts toasts={toasts} />
    </ToastContext.Provider>
  );
}

export function useNotify(): Notify {
  const notify = useContext(ToastContext);
  if (!notify) throw new Error("useNotify must be used inside <ToastProvider>");
  return notify;
}
