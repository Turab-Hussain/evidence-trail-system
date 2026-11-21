import { STATUS_LABEL } from "../../lib/format";
import type { RequirementStatus } from "../../types";

export function StatusPill({ status }: { status: RequirementStatus }) {
  return <span className={`pill pill-${status}`}>{STATUS_LABEL[status]}</span>;
}
