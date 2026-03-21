import { useEffect, useState } from "react";

const MAX_ROWS = 400;

export default function LiveMonitor() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    // Determine WS URL based on current host to support local vs deployed
    let reconnectTimer = null;
    let ws = null;

    const connectWs = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const backendHost = window.location.hostname === "localhost" ? "localhost:8000" : "127.0.0.1:8000";
      const wsUrl = `${protocol}//${backendHost}/ws/live`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          
          // Handle single event or raw event
          const rawEvents = data.type === "BATCH" ? data.payload : [data];
          
          rawEvents.forEach(e => {
            // Unwrap payload if it's a specific event type
            if (["LIVE_THREAT_LOG", "RECON_PACKET", "LIVE_REQUEST"].includes(e.type)) {
              eventBuffer.push(e.payload);
            } else if (e.timestamp && e.url) {
              // Already raw format
              eventBuffer.push(e);
            }
          });
        } catch (e) {
          console.error("Invalid WS message", e);
        }
      };

      ws.onclose = () => {
        console.log("LiveMonitor: WS closed. Reconnecting in 3s...");
        reconnectTimer = setTimeout(connectWs, 3000);
      };
    };

    connectWs();

    // Render Throttling for UI Performance
    const interval = setInterval(() => {
      if (eventBuffer.length > 0) {
        setEvents((prev) => {
          let updated = [...prev, ...eventBuffer];
          eventBuffer = []; // clear buffer

          if (updated.length > MAX_ROWS) {
             // Keep the latest MAX_ROWS
             updated = updated.slice(updated.length - MAX_ROWS);
          }
          return updated;
        });
      }
    }, 50); // 20 FPS

    return () => {
      clearTimeout(reconnectTimer);
      clearInterval(interval);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, []);

  function getColor(e) {
    if (e.anomaly) return "#ff4444";
    if (e.status >= 400) return "#ffbb33";
    return "#00C851";
  }

  return (
    <div className="live-monitor-container" style={{ 
      background: "#111", 
      border: "1px solid #333", 
      borderRadius: "8px", 
      padding: "15px",
      fontFamily: "monospace",
      color: "#ddd"
    }}>
      <h3 style={{ margin: "0 0 10px 0", color: "#fff", borderBottom: "1px solid #333", paddingBottom: "10px" }}>
        LIVE THREAT MONITORING <span style={{fontSize:"12px", color:"#888"}}>(Showing up to 400 reqs)</span>
      </h3>
      <div style={{ height: "400px", overflowY: "auto", overflowX: "hidden" }}>
        <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ color: "#888", borderBottom: "1px solid #222" }}>
              <th style={{ padding: "5px" }}>Time</th>
              <th style={{ padding: "5px" }}>Method</th>
              <th style={{ padding: "5px" }}>Endpoint</th>
              <th style={{ padding: "5px" }}>Status</th>
              <th style={{ padding: "5px" }}>Result</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i} style={{ color: getColor(e), borderBottom: "1px solid #1a1a1a" }}>
                <td style={{ padding: "5px", width: "100px" }}>[{e.timestamp}]</td>
                <td style={{ padding: "5px", width: "60px" }}>{e.method}</td>
                <td style={{ padding: "5px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "200px" }}>{e.endpoint}</td>
                <td style={{ padding: "5px", width: "80px" }}>{e.status}</td>
                <td style={{ padding: "5px" }}>
                  {e.anomaly ? "🔴 " : e.status >= 400 ? "🟡 " : "🟢 "}
                  {e.result}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {events.length === 0 && <div style={{textAlign: "center", color: "#666", marginTop: "20px"}}>Waiting for traffic...</div>}
      </div>
    </div>
  );
}
