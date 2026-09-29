import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, LayerGroup } from "react-leaflet";
import { RISK_COLORS, inr } from "../theme/tokens";

// Interactive risk map: hotspot zones (choropleth-style circles) + togglable
// complaint / withdrawal / ATM point layers, with click-to-drilldown popups.
export default function RiskMap({ zones = [], layers = {}, onDrill }) {
  const [show, setShow] = useState({
    zones: true,
    withdrawals: false,
    complaints: false,
    atms: false,
  });
  const toggle = (k) => setShow((s) => ({ ...s, [k]: !s[k] }));

  const Toggle = ({ k, label, color }) => (
    <button
      onClick={() => toggle(k)}
      aria-pressed={show[k]}
      className={`flex min-h-11 items-center gap-1.5 text-xs px-2 py-1 rounded-lg border ${
        show[k] ? "border-blue-300 bg-blue-50 text-accent" : "border-slate-200 bg-white text-muted"
      }`}
    >
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      {label}
    </button>
  );

  return (
    <div className="relative">
      <div className="absolute z-[1000] top-2 left-2 flex gap-1.5 flex-wrap bg-white/90 backdrop-blur p-1.5 rounded-xl border border-slate-200 shadow-sm">
        <Toggle k="zones" label="Risk zones" color="#EF4444" />
        <Toggle k="withdrawals" label="Withdrawals" color="#F97316" />
        <Toggle k="complaints" label="Complaints" color="#155EEF" />
        <Toggle k="atms" label="ATMs" color="#38BDF8" />
      </div>

      <MapContainer
        center={[11.0, 78.4]}
        zoom={7}
        style={{ height: 460, borderRadius: 12 }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap"
        />

        {show.zones && (
          <LayerGroup>
            {zones.map((z) => {
              const color = RISK_COLORS[z.predicted_risk] || "#EF4444";
              return (
                <CircleMarker
                  key={z.cluster_id}
                  center={[z.lat, z.lon]}
                  radius={Math.min(28, 6 + Math.sqrt(z.withdrawal_count))}
                  pathOptions={{ color, fillColor: color, fillOpacity: 0.35 }}
                  eventHandlers={{ click: () => onDrill && onDrill(z) }}
                >
                  <Popup>
                    <div className="text-sm">
                      <b>{z.dominant_district}</b> — {z.predicted_risk}
                      <br />
                      {z.withdrawal_count} withdrawals · {inr(z.total_amount)}
                      <br />
                      Bank: {z.dominant_bank} · {z.near_landmark || "—"}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </LayerGroup>
        )}

        {show.withdrawals && (
          <LayerGroup>
            {(layers.withdrawals || []).map((p, i) => (
              <CircleMarker
                key={i}
                center={[p.lat, p.lon]}
                radius={3}
                pathOptions={{ color: "#F97316", fillOpacity: 0.6, weight: 0 }}
              />
            ))}
          </LayerGroup>
        )}
        {show.complaints && (
          <LayerGroup>
            {(layers.complaints || []).map((p, i) => (
              <CircleMarker
                key={i}
                center={[p.lat, p.lon]}
                radius={3}
                pathOptions={{ color: "#155EEF", fillOpacity: 0.5, weight: 0 }}
              />
            ))}
          </LayerGroup>
        )}
        {show.atms && (
          <LayerGroup>
            {(layers.atms || []).map((p, i) => (
              <CircleMarker
                key={i}
                center={[p.lat, p.lon]}
                radius={4}
                pathOptions={{ color: "#38BDF8", fillOpacity: 0.7, weight: 0 }}
              >
                <Popup>
                  <div className="text-sm">
                    ATM · {p.bank}
                    <br />
                    {p.landmark} ({p.type})
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </LayerGroup>
        )}
      </MapContainer>
    </div>
  );
}
