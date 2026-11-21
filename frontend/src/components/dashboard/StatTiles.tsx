import type { AccountDashboard } from "../../types";

interface Tile {
  label: string;
  value: number;
  /** Highlights the tile when there is work waiting for the user. */
  attention?: boolean;
}

/** The headline figures across all of the user's projects. */
export function StatTiles({ data }: { data: AccountDashboard }) {
  const tiles: Tile[] = [
    { label: "Projects", value: data.projects },
    { label: "Messages received", value: data.sources },
    { label: "Requirements", value: data.requirements },
    { label: "Waiting for your review", value: data.awaiting_review, attention: data.awaiting_review > 0 },
    { label: "Confirmed by clients", value: data.confirmed },
    { label: "Unclear points to ask about", value: data.open_findings, attention: data.open_findings > 0 },
  ];
  return (
    <ul className="tiles">
      {tiles.map((tile) => (
        <li key={tile.label} data-attention={tile.attention ? "true" : undefined}>
          <b>{tile.value}</b>
          <span>{tile.label}</span>
        </li>
      ))}
    </ul>
  );
}
