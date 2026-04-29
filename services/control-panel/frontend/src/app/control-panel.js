import { authedFetch } from "../services/api-client.js";
import { DENSITY_KEY, SECTION_KEY, TOKEN_KEY } from "../state/preferences.js";
import { fmt, tableSlice } from "../components/format.js";

const metricOrder = [
        ["venues_enabled", "Venues Enabled"],
        ["active_markets", "Active Markets"],
        ["open_gaps", "Open Gaps"],
        ["queued_backfills", "Queued Backfills"],
        ["replay_queued", "Replay Queued"],
        ["risk_decisions_24h", "Risk Decisions (24h)"],
        ["policy_violations_24h", "Policy Violations (24h)"],
        ["orders_24h", "Orders (24h)"],
        ["fills_24h", "Fills (24h)"],
        ["portfolio_gross_exposure", "Portfolio Gross Exposure"],
        ["portfolio_net_exposure", "Portfolio Net Exposure"],
      ];
      let currentSection = "overview";
      let paletteOpen = false;
      let paletteTimer = null;

      function applyDensity() {
        const dense = localStorage.getItem(DENSITY_KEY) === "dense";
        document.getElementById("appLayout").classList.toggle("dense", dense);
        document.getElementById("densityBtn").textContent = dense ? "Density: Dense" : "Density: Comfort";
      }

      function applyRoleVisibility(session) {
        const sections = new Set((session?.sections || []).map(String));
        document.querySelectorAll(".nav-item[data-section]").forEach((el) => {
          const section = el.dataset.section || "";
          el.style.display = sections.has(section) ? "block" : "none";
        });
        const label = document.getElementById("sessionPill");
        label.textContent = `${session?.user_id || "unknown"} · ${session?.role || "none"}`;
      }

      function switchSection(section) {
        currentSection = section;
        localStorage.setItem(SECTION_KEY, section);
        document.querySelectorAll(".nav-item[data-section]").forEach((el) => {
          el.classList.toggle("active", (el.dataset.section || "") === section);
        });
        document.getElementById("workspace-overview").classList.toggle("hidden", section !== "overview");
        document.getElementById("workspace-ingestion").classList.toggle("hidden", section !== "ingestion");
        document.getElementById("workspace-kpi").classList.toggle("hidden", section !== "kpi");
        document.getElementById("workspace-risk").classList.toggle("hidden", section !== "risk");
        document.getElementById("workspace-execution").classList.toggle("hidden", section !== "execution");
        document.getElementById("workspace-charting").classList.toggle("hidden", section !== "charting");
        document.getElementById("workspace-ops").classList.toggle("hidden", section !== "ops");
        document.getElementById("workspace-research").classList.toggle("hidden", section !== "research");
        document.getElementById("workspace-config").classList.toggle("hidden", section !== "config");
      }

      function renderOverview(data) {
        const grid = document.getElementById("metricsGrid");
        grid.innerHTML = "";
        for (const [key, label] of metricOrder) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          grid.appendChild(card);
        }

        const tbody = document.querySelector("#moduleTable tbody");
        tbody.innerHTML = "";
        for (const module of tableSlice(data.modules, 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${module.name}</td><td><span class="status ${module.status}">${module.status.toUpperCase()}</span></td>`;
          tbody.appendChild(tr);
        }
      }

      async function loadOverview() {
        const res = await authedFetch('/api/v1/control-panel/overview');
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderOverview(data);
      }

      function renderIngestion(data) {
        const metricMap = [
          ["open_gaps", "Open Gaps"],
          ["queued_backfills", "Queued Backfills"],
          ["failed_backfills_24h", "Failed Backfills (24h)"],
          ["replay_failed_24h", "Replay Failed (24h)"],
          ["coverage_ratio_avg", "Coverage Ratio Avg"],
          ["symbols_with_open_gaps", "Symbols With Open Gaps"],
        ];
        const m = document.getElementById("ingestionMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }

        const connectorBody = document.querySelector("#connectorTable tbody");
        connectorBody.innerHTML = "";
        for (const row of tableSlice(data.connector_health, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}</td><td>${row.symbol} <button class="btn mini" onclick="openChartWorkbench('${row.venue}','${row.symbol}','1m')">Chart</button></td><td><span class="status ${row.status === "online" ? "online" : "degraded"}">${row.status.toUpperCase()}</span></td><td>${row.updated_at || "-"}</td>`;
          connectorBody.appendChild(tr);
        }

        const backfillBody = document.querySelector("#backfillTable tbody");
        backfillBody.innerHTML = "";
        for (const row of tableSlice(data.backfill_recent, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.status}</td><td>${row.venue}:${row.symbol}</td><td>${row.attempt_count}</td>`;
          backfillBody.appendChild(tr);
        }

        const replayBody = document.querySelector("#replayTable tbody");
        replayBody.innerHTML = "";
        for (const row of tableSlice(data.replay_recent, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.status}</td><td>${row.venue}:${row.symbol}</td><td>${row.started_at || "-"}</td>`;
          replayBody.appendChild(tr);
        }
      }

      async function loadIngestion() {
        const res = await authedFetch('/api/v1/control-panel/ingestion?status_lookback_hours=24&coverage_window_hours=24&row_limit=20');
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderIngestion(data);
      }

      async function submitBackfillWindow() {
        const payload = {
          venue: document.getElementById("bfVenue").value.trim(),
          symbol: document.getElementById("bfSymbol").value.trim(),
          from_ts: document.getElementById("bfFrom").value.trim(),
          to_ts: document.getElementById("bfTo").value.trim(),
          justification: document.getElementById("bfJustification").value.trim(),
        };
        const out = document.getElementById("bfResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/backfill-window", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Accepted: ${data.result?.status || "ok"} | missing_after=${data.result?.missing_after_fetch_count ?? "-"}`;
        await loadIngestion();
      }

      function renderIngestionKpi(data) {
        const metricMap = [
          ["active_markets", "Active Markets"],
          ["markets_meeting_ohlcv_target", "OHLCV Target Met"],
          ["markets_meeting_tick_sla", "Tick SLA Met"],
          ["markets_meeting_both", "Both KPI Met"],
          ["avg_ohlcv_progress_pct", "Avg OHLCV Progress %"],
          ["worst_tick_lag_seconds", "Worst Tick Lag (s)"],
        ];
        const m = document.getElementById("kpiMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }

        const body = document.querySelector("#kpiTable tbody");
        body.innerHTML = "";
        for (const row of tableSlice(data.rows, 300)) {
          const tr = document.createElement("tr");
          const kpiState = row.meets_both_kpi ? "PASS" : "WARN";
          const kpiClass = row.meets_both_kpi ? "online" : "degraded";
          tr.innerHTML = `<td>${row.venue}:${row.symbol} <button class="btn mini" onclick="openChartWorkbench('${row.venue}','${row.symbol}','1m')">Chart</button></td><td>${fmt(row.ohlcv_1m_count)} / ${fmt(row.ohlcv_target)}</td><td>${fmt(row.ohlcv_progress_pct)}%</td><td>${row.last_ohlcv_bucket || "-"}</td><td>${fmt(row.ticks_5m)}</td><td>${row.last_tick_ts || "-"}</td><td>${row.tick_lag_seconds ?? "-"}</td><td><span class="status ${kpiClass}">${kpiState}</span></td>`;
          body.appendChild(tr);
        }
      }

      async function loadIngestionKpi() {
        const target = Math.max(10000, Number(document.getElementById("kpiTargetBars").value || 130000));
        const tickSla = Math.max(5, Number(document.getElementById("kpiTickSla").value || 120));
        const qs = new URLSearchParams({
          target_1m_bars: String(target),
          tick_sla_seconds: String(tickSla),
          row_limit: "300",
        });
        const res = await authedFetch(`/api/v1/control-panel/ingestion/kpi?${qs.toString()}`);
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderIngestionKpi(data);
      }

      function renderRiskPortfolio(data) {
        const metricMap = [
          ["policy_violations_24h", "Policy Violations (24h)"],
          ["risk_decisions_24h", "Risk Decisions (24h)"],
          ["kill_switch_on_symbols", "Kill Switch Symbols"],
          ["portfolio_gross_exposure", "Portfolio Gross Exposure"],
          ["portfolio_net_exposure", "Portfolio Net Exposure"],
          ["available_equity_headroom", "Available Equity Headroom"],
        ];
        const m = document.getElementById("riskMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }

        const strategyBody = document.querySelector("#strategyTable tbody");
        strategyBody.innerHTML = "";
        for (const row of tableSlice(data.strategy_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}:${row.symbol} <button class="btn mini" onclick="openChartWorkbench('${row.venue}','${row.symbol}','1m')">Chart</button></td><td>${row.decisions_24h}</td><td>${fmt(row.avg_confidence)}</td><td>${row.violations_24h}</td><td><span class="status ${row.status === "healthy" ? "online" : "degraded"}">${row.status.toUpperCase()}</span></td>`;
          strategyBody.appendChild(tr);
        }

        const expBody = document.querySelector("#exposureTable tbody");
        expBody.innerHTML = "";
        for (const row of tableSlice(data.symbol_exposure_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}:${row.symbol}:${row.timeframe}</td><td>${fmt(row.exposure_notional)}</td><td>${fmt(row.drawdown_pct)}</td><td>${row.kill_switch_enabled ? "ON" : "OFF"}</td>`;
          expBody.appendChild(tr);
        }

        const vioBody = document.querySelector("#violationsTable tbody");
        vioBody.innerHTML = "";
        for (const row of tableSlice(data.recent_violations, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}:${row.symbol}</td><td>${row.reason}</td><td>${(row.violations || []).join(", ")}</td>`;
          vioBody.appendChild(tr);
        }

        const limits = data.limits || {};
        document.getElementById("rlMinConfidence").value = limits.min_confidence ?? "";
        document.getElementById("rlMaxNotional").value = limits.max_notional ?? "";
        document.getElementById("rlMaxDrawdown").value = limits.max_drawdown_pct ?? "";
        document.getElementById("rlMaxSymbolExposure").value = limits.max_symbol_exposure_notional ?? "";
        document.getElementById("rlMaxPortfolioGross").value = limits.max_portfolio_gross_exposure_notional ?? "";
        document.getElementById("rlMinAvailableEquity").value = limits.min_available_equity ?? "";
      }

      async function loadRiskPortfolio() {
        const res = await authedFetch("/api/v1/control-panel/risk-portfolio?row_limit=20");
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderRiskPortfolio(data);
      }

      async function submitRiskLimits() {
        const payload = {
          min_confidence: Number(document.getElementById("rlMinConfidence").value),
          max_notional: Number(document.getElementById("rlMaxNotional").value),
          max_drawdown_pct: Number(document.getElementById("rlMaxDrawdown").value),
          max_symbol_exposure_notional: Number(document.getElementById("rlMaxSymbolExposure").value),
          max_portfolio_gross_exposure_notional: Number(document.getElementById("rlMaxPortfolioGross").value),
          min_available_equity: Number(document.getElementById("rlMinAvailableEquity").value),
          justification: document.getElementById("rlJustification").value.trim(),
        };
        const out = document.getElementById("riskLimitsResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/risk-limits", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated by ${data.updated_by}`;
        await loadRiskPortfolio();
      }

      async function submitKillSwitch() {
        const payload = {
          scope: document.getElementById("ksScope").value.trim(),
          venue: document.getElementById("ksVenue").value.trim(),
          symbol: document.getElementById("ksSymbol").value.trim(),
          enabled: document.getElementById("ksEnabled").value.trim().toLowerCase() === "true",
          justification: document.getElementById("ksJustification").value.trim(),
        };
        const out = document.getElementById("killSwitchResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/risk/kill-switch", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated (${data.scope}) affected_rows=${data.affected_rows}`;
        await loadRiskPortfolio();
      }

      function renderExecution(data) {
        const metricMap = [
          ["orders_total", "Orders Total"],
          ["submitted_24h", "Submitted (24h)"],
          ["filled_24h", "Filled (24h)"],
          ["rejected_24h", "Rejected (24h)"],
          ["cancelled_24h", "Cancelled (24h)"],
          ["reconciliation_issues_open", "Recon Issues"],
        ];
        const m = document.getElementById("executionMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }

        const ordersBody = document.querySelector("#ordersTable tbody");
        ordersBody.innerHTML = "";
        for (const row of tableSlice(data.order_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.order_id}</td><td>${row.venue}:${row.symbol} <button class="btn mini" onclick="openChartWorkbench('${row.venue}','${row.symbol}','1m')">Chart</button></td><td>${row.side}</td><td>${row.status}</td><td>${fmt(row.requested_notional)}</td><td>${row.updated_at || "-"}</td>`;
          ordersBody.appendChild(tr);
        }

        const cmdBody = document.querySelector("#commandsTable tbody");
        cmdBody.innerHTML = "";
        for (const row of tableSlice(data.command_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.action}</td><td>${row.order_id}</td><td>${row.accepted ? "YES" : "NO"}</td><td>${row.created_at || "-"}</td>`;
          cmdBody.appendChild(tr);
        }

        const recBody = document.querySelector("#reconciliationTable tbody");
        recBody.innerHTML = "";
        for (const row of tableSlice(data.reconciliation_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.order_id}</td><td>${row.venue}:${row.symbol}</td><td>${row.status}</td><td>${row.updated_at || "-"}</td>`;
          recBody.appendChild(tr);
        }

        const bdBody = document.querySelector("#brokerDiagTable tbody");
        bdBody.innerHTML = "";
        for (const row of tableSlice(data.broker_diagnostics, 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.event_type}</td><td>${row.count_24h}</td>`;
          bdBody.appendChild(tr);
        }
      }

      async function loadExecution() {
        const res = await authedFetch("/api/v1/control-panel/execution?row_limit=25");
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderExecution(data);
      }

      async function submitExecutionCommand() {
        const payload = {
          order_id: document.getElementById("exOrderId").value.trim(),
          action: document.getElementById("exAction").value.trim(),
          new_notional: document.getElementById("exNotional").value.trim() ? Number(document.getElementById("exNotional").value.trim()) : null,
          justification: document.getElementById("exJustification").value.trim(),
        };
        const out = document.getElementById("executionCmdResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/execution/command", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Accepted: ${data.action} for ${data.order_id}`;
        await loadExecution();
      }

      function renderChartingWorkbench(data) {
        const profile = data.profile || {};
        const metrics = [
          ["Open Gaps", profile.open_gap_count ?? 0],
          ["Ingest Enabled", profile.ingest_enabled ? "YES" : "NO"],
          ["Market Enabled", profile.market_enabled ? "YES" : "NO"],
          ["Asset Class", profile.asset_class || "unknown"],
        ];
        const grid = document.getElementById("cwMetrics");
        grid.innerHTML = "";
        for (const [label, value] of metrics) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${value}</div>`;
          grid.appendChild(card);
        }

        const tbody = document.querySelector("#cwProfileTable tbody");
        const latestBar = profile.latest_bar || {};
        const latestRisk = profile.latest_risk_state || {};
        const latestExec = profile.latest_execution_state || {};
        tbody.innerHTML = `
          <tr><th>Latest Bar</th><td>${latestBar.bucket_start || "-"} | O:${fmt(latestBar.open)} H:${fmt(latestBar.high)} L:${fmt(latestBar.low)} C:${fmt(latestBar.close)}</td></tr>
          <tr><th>Risk State</th><td>Exposure:${fmt(latestRisk.exposure_notional)} Drawdown:${fmt(latestRisk.drawdown_pct)} KillSwitch:${latestRisk.kill_switch_enabled ? "ON" : "OFF"}</td></tr>
          <tr><th>Execution State</th><td>${latestExec.status || "-"} ${latestExec.side || ""} ${fmt(latestExec.requested_notional)}</td></tr>
        `;

        const chartLink = data.links?.full_chart || "/";
        document.getElementById("cwFrame").src = chartLink;
        document.getElementById("cwLinkLabel").textContent = `${profile.venue}:${profile.symbol}:${profile.timeframe} → ${chartLink}`;
      }

      async function loadChartingWorkbench(venue, symbol, timeframe) {
        if (venue) document.getElementById("cwVenue").value = venue;
        if (symbol) document.getElementById("cwSymbol").value = symbol;
        if (timeframe) document.getElementById("cwTimeframe").value = timeframe;
        const v = document.getElementById("cwVenue").value.trim();
        const s = document.getElementById("cwSymbol").value.trim();
        const tf = document.getElementById("cwTimeframe").value.trim() || "1m";

        const qs = new URLSearchParams({venue: v, symbol: s, timeframe: tf});
        const res = await authedFetch(`/api/v1/control-panel/charting/profile?${qs.toString()}`);
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderChartingWorkbench(data);
      }

      function renderOps(data) {
        const metricMap = [
          ["alerts_open", "Alerts Open"],
          ["alerts_critical", "Critical Alerts"],
          ["incidents_open", "Incidents Open"],
          ["sla_breached_open_alerts", "SLA Breached Alerts"],
          ["runbooks_24h", "Runbooks (24h)"],
          ["mttr_minutes_7d", "MTTR Minutes (7d)"],
        ];
        const m = document.getElementById("opsMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }

        const alertBody = document.querySelector("#alertTable tbody");
        alertBody.innerHTML = "";
        for (const row of tableSlice(data.alert_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.title}</td><td>${row.severity}</td><td>${row.status}</td><td>${row.owner || "-"}</td><td>${row.sla_due_at || "-"}</td><td><button class="btn mini" onclick="submitAlertAction('${row.alert_id}','acknowledge')">Acknowledge</button> <button class="btn mini" onclick="submitAlertAction('${row.alert_id}','incident')">Incident</button></td>`;
          alertBody.appendChild(tr);
        }

        const incidentBody = document.querySelector("#incidentTable tbody");
        incidentBody.innerHTML = "";
        for (const row of tableSlice(data.incident_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.incident_id}</td><td>${row.severity}</td><td>${row.status}</td><td>${row.owner || "-"}</td><td>${row.opened_at || "-"}</td>`;
          incidentBody.appendChild(tr);
        }

        const runbookBody = document.querySelector("#runbookTable tbody");
        runbookBody.innerHTML = "";
        for (const row of tableSlice(data.runbook_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.runbook_code}</td><td>${row.action}</td><td>${row.status}</td><td>${row.incident_id || "-"}</td><td>${row.created_at || "-"}</td>`;
          runbookBody.appendChild(tr);
        }
      }

      async function loadOps() {
        const res = await authedFetch("/api/v1/control-panel/ops?row_limit=25");
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderOps(data);
      }

      async function submitAlertAction(alertId, action) {
        const res = await authedFetch("/api/v1/control-panel/ops/alerts/action", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            alert_id: alertId,
            action,
            owner: "ops@desk",
            note: "action from ops workspace",
            justification: `Operator action ${action} executed from control panel`,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          alert(`Action rejected: ${data.detail || "unknown error"}`);
          return;
        }
        await loadOps();
      }

      async function submitRunbook() {
        const payload = {
          incident_id: document.getElementById("rbIncidentId").value.trim() || null,
          runbook_code: document.getElementById("rbCode").value.trim(),
          action: document.getElementById("rbAction").value.trim(),
          justification: document.getElementById("rbJustification").value.trim(),
          operator_note: document.getElementById("rbNote").value.trim(),
        };
        const out = document.getElementById("runbookResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ops/runbook/execute", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Runbook completed: ${data.runbook_code} (${data.execution_id})`;
        await loadOps();
      }

      async function submitOpsAlert() {
        const payload = {
          source: document.getElementById("oaSource").value.trim(),
          severity: document.getElementById("oaSeverity").value.trim(),
          title: document.getElementById("oaTitle").value.trim(),
          sla_minutes: Number(document.getElementById("oaSlaMinutes").value.trim() || "30"),
          signal_ref: document.getElementById("oaSignalRef").value.trim() || null,
        };
        const out = document.getElementById("opsAlertResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ops/alerts/ingest", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Alert created: ${data.alert_id}`;
        await loadOps();
      }

      function renderResearch(data) {
        const metricMap = [
          ["datasets_ready", "Datasets Ready"],
          ["backtests_24h", "Backtests (24h)"],
          ["models_registered", "Models Registered"],
          ["promotion_ready_models", "Promotion Ready"],
          ["avg_readiness_score", "Avg Readiness"],
          ["best_sharpe_30d", "Best Sharpe (30d)"],
        ];
        const m = document.getElementById("researchMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }

        const datasetBody = document.querySelector("#datasetTable tbody");
        datasetBody.innerHTML = "";
        for (const row of tableSlice(data.dataset_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.dataset_code}</td><td>${row.venue}:${row.symbol}:${row.timeframe}</td><td>${fmt(row.row_count)}</td><td>${row.status}</td><td>${row.lineage_ref || "-"}</td>`;
          datasetBody.appendChild(tr);
        }

        const backtestBody = document.querySelector("#backtestTable tbody");
        backtestBody.innerHTML = "";
        for (const row of tableSlice(data.backtest_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.run_id}</td><td>${row.strategy_code}</td><td>${row.status}</td><td>${fmt(row.pnl)}</td><td>${fmt(row.sharpe)}</td>`;
          backtestBody.appendChild(tr);
        }

        const modelBody = document.querySelector("#modelTable tbody");
        modelBody.innerHTML = "";
        for (const row of tableSlice(data.model_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.model_name}</td><td>${row.model_version}</td><td>${row.stage}</td><td>${row.gate_status}</td><td>${fmt(row.readiness_score)}</td>`;
          modelBody.appendChild(tr);
        }

        if ((data.dataset_rows || []).length > 0) {
          document.getElementById("btDatasetId").value = data.dataset_rows[0].dataset_id;
        }
      }

      async function loadResearch() {
        const res = await authedFetch("/api/v1/control-panel/research?row_limit=25");
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderResearch(data);
      }

      async function submitBacktest() {
        const payload = {
          dataset_id: document.getElementById("btDatasetId").value.trim(),
          strategy_code: document.getElementById("btStrategyCode").value.trim(),
          model_version: document.getElementById("btModelVersion").value.trim(),
          justification: document.getElementById("btJustification").value.trim(),
        };
        const out = document.getElementById("btResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/research/backtest", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Backtest accepted: ${data.run_id}`;
        await loadResearch();
      }

      async function submitModelPromotion() {
        const payload = {
          model_name: document.getElementById("mpModelName").value.trim(),
          model_version: document.getElementById("mpModelVersion").value.trim(),
          stage: document.getElementById("mpStage").value.trim(),
          gate_status: document.getElementById("mpGateStatus").value.trim(),
          readiness_score: Number(document.getElementById("mpReadinessScore").value.trim()),
          experiment_ref: document.getElementById("mpExperimentRef").value.trim(),
          justification: document.getElementById("mpJustification").value.trim(),
        };
        const out = document.getElementById("promoteResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/research/model/promote", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Model gate updated: ${data.model_name}:${data.model_version} (${data.stage}/${data.gate_status})`;
        await loadResearch();
      }

      function renderConfig(data) {
        const metricMap = [
          ["keys_total", "Keys (Env)"],
          ["high_risk_keys", "High Risk Keys"],
          ["pending_changes", "Pending Changes"],
          ["applied_24h", "Applied (24h)"],
          ["rollbacks_7d", "Rollbacks (7d)"],
          ["drift_keys", "Drifted Keys"],
        ];
        const m = document.getElementById("configMetrics");
        m.innerHTML = "";
        for (const [key, label] of metricMap) {
          const card = document.createElement("article");
          card.className = "card";
          card.innerHTML = `<div class="muted">${label}</div><div class="metric">${fmt(data.metrics[key])}</div>`;
          m.appendChild(card);
        }
        const cfgBody = document.querySelector("#configTable tbody");
        cfgBody.innerHTML = "";
        for (const row of tableSlice(data.config_rows, 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.config_key}</td><td><code>${JSON.stringify(row.config_value)}</code></td><td>${row.value_type}</td><td>${row.risk_level}</td><td>${row.min_role}</td>`;
          cfgBody.appendChild(tr);
        }

        const changeBody = document.querySelector("#changeTable tbody");
        changeBody.innerHTML = "";
        for (const row of tableSlice(data.change_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.change_id}</td><td>${row.config_key}</td><td>${row.environment}</td><td>${row.status}</td><td>${row.requested_by}</td>`;
          changeBody.appendChild(tr);
        }
        if ((data.change_rows || []).length > 0) {
          document.getElementById("ccChangeId").value = data.change_rows[0].change_id;
        }

        const histBody = document.querySelector("#configHistoryTable tbody");
        histBody.innerHTML = "";
        for (const row of tableSlice(data.history_rows, 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.action}</td><td>${row.actor}</td><td>${row.change_id}</td><td>${row.created_at || "-"}</td>`;
          histBody.appendChild(tr);
        }
      }

      async function loadConfig() {
        const env = document.getElementById("cfgEnvironment").value.trim() || "dev";
        const qs = new URLSearchParams({ environment: env, row_limit: "30" });
        const res = await authedFetch(`/api/v1/control-panel/config?${qs.toString()}`);
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          throw new Error("unauthorized");
        }
        const data = await res.json();
        applyRoleVisibility(data.session || {});
        renderConfig(data);
      }

      function parseJsonLiteral(raw) {
        try {
          return JSON.parse(raw);
        } catch (_e) {
          return raw;
        }
      }

      async function proposeConfigChange() {
        const payload = {
          config_key: document.getElementById("cpConfigKey").value.trim(),
          environment: document.getElementById("cfgEnvironment").value.trim() || "dev",
          proposed_value: parseJsonLiteral(document.getElementById("cpProposedValue").value.trim()),
          justification: document.getElementById("cpJustification").value.trim(),
        };
        const out = document.getElementById("cpResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/config/propose", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Proposal ${data.status}: ${data.change_id}`;
        await loadConfig();
      }

      async function approveConfigChange() {
        const payload = {
          change_id: document.getElementById("ccChangeId").value.trim(),
          justification: document.getElementById("ccJustification").value.trim(),
        };
        const out = document.getElementById("ccResult");
        out.textContent = "Submitting approve...";
        const res = await authedFetch("/api/v1/control-panel/config/approve", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Approved: ${data.change_id}`;
        await loadConfig();
      }

      async function applyConfigChange() {
        const payload = {
          change_id: document.getElementById("ccChangeId").value.trim(),
          justification: document.getElementById("ccJustification").value.trim(),
        };
        const out = document.getElementById("ccResult");
        out.textContent = "Submitting apply...";
        const res = await authedFetch("/api/v1/control-panel/config/apply", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Applied: ${data.change_id}`;
        await loadConfig();
      }

      async function rollbackConfigChange() {
        const payload = {
          change_id: document.getElementById("ccChangeId").value.trim(),
          justification: document.getElementById("ccRollbackJustification").value.trim(),
        };
        const out = document.getElementById("ccResult");
        out.textContent = "Submitting rollback...";
        const res = await authedFetch("/api/v1/control-panel/config/rollback", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Rollback completed for ${data.rollback_of}`;
        await loadConfig();
      }

      function openPalette() {
        paletteOpen = true;
        document.getElementById("paletteModal").classList.remove("hidden");
        document.getElementById("paletteInput").focus();
      }
      function closePalette() {
        paletteOpen = false;
        document.getElementById("paletteModal").classList.add("hidden");
      }
      async function searchPalette() {
        const q = document.getElementById("paletteInput").value.trim();
        const tbody = document.getElementById("paletteResults");
        tbody.innerHTML = "";
        if (q.length < 2) return;
        const qs = new URLSearchParams({ q });
        const res = await authedFetch(`/api/v1/control-panel/search?${qs.toString()}`);
        if (!res.ok) return;
        const data = await res.json();
        for (const row of tableSlice(data.results, 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.type}</td><td>${row.label}</td><td><button class="btn mini" onclick="switchSection('${row.section}');closePalette();">${row.section}</button></td>`;
          tbody.appendChild(tr);
        }
      }

      function openChartWorkbench(venue, symbol, timeframe = "1m") {
        switchSection("charting");
        loadChartingWorkbench(venue, symbol, timeframe).catch(console.error);
      }
      window.openChartWorkbench = openChartWorkbench;
      window.submitAlertAction = submitAlertAction;
      window.switchSection = switchSection;
      window.closePalette = closePalette;

      document.querySelectorAll(".nav-item[data-section]").forEach((el) => {
        el.addEventListener("click", async () => {
          const section = el.dataset.section || "overview";
          switchSection(section);
          if (section === "ingestion") {
            await loadIngestion();
          } else if (section === "kpi") {
            await loadIngestionKpi();
          } else if (section === "risk") {
            await loadRiskPortfolio();
          } else if (section === "execution") {
            await loadExecution();
          } else if (section === "charting") {
            await loadChartingWorkbench();
          } else if (section === "ops") {
            await loadOps();
          } else if (section === "research") {
            await loadResearch();
          } else if (section === "config") {
            await loadConfig();
          } else {
            await loadOverview();
          }
        });
      });
      document.getElementById("backfillBtn").addEventListener("click", () => submitBackfillWindow().catch(console.error));
      document.getElementById("kpiLoadBtn").addEventListener("click", () => loadIngestionKpi().catch(console.error));
      document.getElementById("riskLimitsBtn").addEventListener("click", () => submitRiskLimits().catch(console.error));
      document.getElementById("killSwitchBtn").addEventListener("click", () => submitKillSwitch().catch(console.error));
      document.getElementById("executionCmdBtn").addEventListener("click", () => submitExecutionCommand().catch(console.error));
      document.getElementById("cwLoadBtn").addEventListener("click", () => loadChartingWorkbench().catch(console.error));
      document.getElementById("runbookBtn").addEventListener("click", () => submitRunbook().catch(console.error));
      document.getElementById("opsAlertBtn").addEventListener("click", () => submitOpsAlert().catch(console.error));
      document.getElementById("backtestBtn").addEventListener("click", () => submitBacktest().catch(console.error));
      document.getElementById("promoteBtn").addEventListener("click", () => submitModelPromotion().catch(console.error));
      document.getElementById("cfgLoadBtn").addEventListener("click", () => loadConfig().catch(console.error));
      document.getElementById("cpProposeBtn").addEventListener("click", () => proposeConfigChange().catch(console.error));
      document.getElementById("ccApproveBtn").addEventListener("click", () => approveConfigChange().catch(console.error));
      document.getElementById("ccApplyBtn").addEventListener("click", () => applyConfigChange().catch(console.error));
      document.getElementById("ccRollbackBtn").addEventListener("click", () => rollbackConfigChange().catch(console.error));
      document.getElementById("densityBtn").addEventListener("click", () => {
        const dense = localStorage.getItem(DENSITY_KEY) === "dense";
        localStorage.setItem(DENSITY_KEY, dense ? "comfort" : "dense");
        applyDensity();
      });
      document.getElementById("paletteBtn").addEventListener("click", () => openPalette());
      document.getElementById("paletteCloseBtn").addEventListener("click", () => closePalette());
      document.getElementById("paletteInput").addEventListener("input", () => {
        if (paletteTimer) clearTimeout(paletteTimer);
        paletteTimer = setTimeout(() => { searchPalette().catch(console.error); }, 120);
      });
      document.addEventListener("keydown", (ev) => {
        if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
          ev.preventDefault();
          openPalette();
        } else if (ev.key === "Escape" && paletteOpen) {
          closePalette();
        }
      });
      document.getElementById('refreshBtn').addEventListener('click', () => {
        if (currentSection === "ingestion") {
          loadIngestion().catch(console.error);
        } else if (currentSection === "kpi") {
          loadIngestionKpi().catch(console.error);
        } else if (currentSection === "risk") {
          loadRiskPortfolio().catch(console.error);
        } else if (currentSection === "execution") {
          loadExecution().catch(console.error);
        } else if (currentSection === "charting") {
          loadChartingWorkbench().catch(console.error);
        } else if (currentSection === "ops") {
          loadOps().catch(console.error);
        } else if (currentSection === "research") {
          loadResearch().catch(console.error);
        } else if (currentSection === "config") {
          loadConfig().catch(console.error);
        } else {
          loadOverview().catch(console.error);
        }
      });
      applyDensity();
      const initialSection = localStorage.getItem(SECTION_KEY) || "overview";
      switchSection(initialSection);
      if (initialSection === "ingestion") loadIngestion().catch(console.error);
      else if (initialSection === "kpi") loadIngestionKpi().catch(console.error);
      else if (initialSection === "risk") loadRiskPortfolio().catch(console.error);
      else if (initialSection === "execution") loadExecution().catch(console.error);
      else if (initialSection === "charting") loadChartingWorkbench().catch(console.error);
      else if (initialSection === "ops") loadOps().catch(console.error);
      else if (initialSection === "research") loadResearch().catch(console.error);
      else if (initialSection === "config") loadConfig().catch(console.error);
      else loadOverview().catch(console.error);
