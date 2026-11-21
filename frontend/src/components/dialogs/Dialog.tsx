import { useEffect, useRef, type ReactNode } from "react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  /** id of the heading inside ``children`` that names the dialog. */
  labelledBy: string;
  children: ReactNode;
}

/**
 * Modal built on the native <dialog> element, which gives us focus trapping,
 * Escape-to-close and a backdrop for free. Children mount only while open, so
 * forms start fresh each time.
 */
export function Dialog({ open, onClose, labelledBy, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby={labelledBy}
      onClose={onClose}
      // The dialog has no padding, so a click whose target is the dialog itself hit the backdrop.
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {open ? children : null}
    </dialog>
  );
}
