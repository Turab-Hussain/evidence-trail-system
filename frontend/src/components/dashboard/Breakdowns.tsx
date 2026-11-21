import { CHANNEL_LABEL, STATUS_LABEL, STATUS_ORDER, plural } from "../../lib/format";
import type { AccountDashboard, Channel } from "../../types";

/** Requirements by status: a proportional bar plus a legend with exact counts. */
export function StatusBreakdown({ data }: { data: AccountDashboard }) {
  const total = data.requirements;
  return (
    <section className="card" aria-label="Requirements by status">
      <h3>Requirements by status</h3>
      {total === 0 ? (
        <p className="muted">Nothing extracted yet.</p>
      ) : (
        <>
          <div className="strip" role="img" aria-label={`${plural(total, "requirement")} by status`}>
            {STATUS_ORDER.filter((status) => data.by_status[status] > 0).map((status) => (
              <i key={status} className={`seg-${status}`} style={{ flexGrow: data.by_status[status] }} />
            ))}
          </div>
          <ul className="legend">
            {STATUS_ORDER.map((status) => (
              <li key={status}>
                <i className={`swatch seg-${status}`} aria-hidden="true" />
                <span>{STATUS_LABEL[status]}</span>
                <b>{data.by_status[status]}</b>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

const CHANNELS: Channel[] = ["whatsapp", "email", "meeting_transcript", "document"];

/** Where the client's words came from. */
export function ChannelBreakdown({ data }: { data: AccountDashboard }) {
  const largest = Math.max(1, ...CHANNELS.map((channel) => data.by_channel[channel]));
  return (
    <section className="card" aria-label="Messages by channel">
      <h3>Messages by channel</h3>
      {data.sources === 0 ? (
        <p className="muted">No messages yet.</p>
      ) : (
        <ul className="bars">
          {CHANNELS.map((channel) => (
            <li key={channel}>
              <span>{CHANNEL_LABEL[channel]}</span>
              <span className="bar" aria-hidden="true">
                <i style={{ width: `${(data.by_channel[channel] / largest) * 100}%` }} />
              </span>
              <b>{data.by_channel[channel]}</b>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
