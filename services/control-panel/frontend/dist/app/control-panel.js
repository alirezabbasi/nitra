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
          ["raw_capture_rows_24h", "Raw Captures (24h)"],
          ["sequence_anomalies_24h", "Seq Anomalies (24h)"],
          ["raw_lake_objects_24h", "Raw Lake Objects (24h)"],
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
          tr.innerHTML = `<td>${row.venue}</td><td>${row.symbol} <button class="btn mini" onclick="openChartTab('${row.venue}','${row.symbol}','5m')">Chart Tab</button></td><td><span class="status ${row.status === "online" ? "online" : "degraded"}">${row.status.toUpperCase()}</span></td><td>${row.updated_at || "-"}</td>`;
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

        const rawBody = document.querySelector("#rawCaptureTable tbody");
        rawBody.innerHTML = "";
        for (const row of tableSlice(data.raw_capture_recent || [], 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}:${row.symbol}</td><td>${row.sequence_status}</td><td>${row.sequence_numeric ?? "-"}</td><td>${row.previous_sequence_numeric ?? "-"}</td><td>${row.sequence_gap ?? "-"}</td><td>${row.source_topic}:${row.source_partition}@${row.source_offset}</td>`;
          rawBody.appendChild(tr);
        }

        const manifestBody = document.querySelector("#rawLakeManifestTable tbody");
        manifestBody.innerHTML = "";
        for (const row of tableSlice(data.raw_lake_manifest_recent || [], 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.partition_year}-${String(row.partition_month).padStart(2, "0")}-${String(row.partition_day).padStart(2, "0")} ${String(row.partition_hour).padStart(2, "0")}:00</td><td>${row.venue}:${row.symbol}</td><td>${fmt(row.row_count)}</td><td>${row.min_source_offset}..${row.max_source_offset}</td><td title="${row.object_key}">${row.object_key}</td>`;
          manifestBody.appendChild(tr);
        }

        const replayManifestBody = document.querySelector("#replayManifestTable tbody");
        replayManifestBody.innerHTML = "";
        for (const row of tableSlice(data.replay_manifest_recent || [], 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td title="${row.manifest_id}">${row.manifest_id.slice(0, 8)}</td><td>${row.range_from_ts || "-"} .. ${row.range_to_ts || "-"}</td><td>${fmt(row.object_count)}</td><td>${fmt(row.selected_row_count)}</td><td>${row.min_source_offset ?? "-"}..${row.max_source_offset ?? "-"}</td>`;
          replayManifestBody.appendChild(tr);
        }

        const policyMetrics = document.getElementById("failoverPolicyMetrics");
        const runtime = data.failover_runtime || {};
        policyMetrics.innerHTML = `
          <div class="small">Configured Enabled Venues: <strong>${fmt(runtime.configured_enabled_venues)}</strong></div>
          <div class="small">Configured Disabled Venues: <strong>${fmt(runtime.configured_disabled_venues)}</strong></div>
          <div class="small">Active Market Venues: <strong>${(runtime.active_market_venues || []).join(", ") || "-"}</strong></div>
          <div class="small">Degraded Market Venues: <strong>${(runtime.degraded_market_venues || []).join(", ") || "-"}</strong></div>
        `;

        const policyBody = document.querySelector("#failoverPolicyTable tbody");
        policyBody.innerHTML = "";
        for (const row of tableSlice(data.failover_policies || [], 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}</td><td>${row.enabled ? "ON" : "OFF"}</td><td>${row.primary_endpoint}</td><td>${(row.secondary_endpoints || []).join(", ") || "-"}</td><td>${row.failure_threshold}</td><td>${row.cooldown_seconds}</td><td>${row.reconnect_backoff_seconds}/${row.max_backoff_seconds}</td><td>${row.request_timeout_seconds}</td><td>${fmt(row.jitter_pct)}</td><td>${row.updated_by}</td>`;
          policyBody.appendChild(tr);
        }

        const sessionMetrics = document.getElementById("sessionPolicyMetrics");
        const sessionRuntime = data.session_runtime || {};
        sessionMetrics.innerHTML = `
          <div class="small">Enabled Session Policies: <strong>${fmt(sessionRuntime.configured_enabled_venues)}</strong></div>
          <div class="small">Disabled Session Policies: <strong>${fmt(sessionRuntime.configured_disabled_venues)}</strong></div>
          <div class="small">Capital Session Cached: <strong>${sessionRuntime.capital_session_cached ? "YES" : "NO"}</strong></div>
          <div class="small">Capital Session Expires In (s): <strong>${fmt(sessionRuntime.capital_session_expires_in_seconds ?? "-")}</strong></div>
        `;
        const sessionBody = document.querySelector("#sessionPolicyTable tbody");
        sessionBody.innerHTML = "";
        for (const row of tableSlice(data.session_policies || [], 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}</td><td>${row.enabled ? "ON" : "OFF"}</td><td>${row.auth_mode}</td><td>${row.token_ttl_seconds}</td><td>${row.refresh_lead_seconds}</td><td>${row.max_refresh_retries}</td><td>${row.lockout_cooldown_seconds}</td><td>${row.classify_401}/${row.classify_403}/${row.classify_429}/${row.classify_5xx}</td><td>${row.updated_by}</td>`;
          sessionBody.appendChild(tr);
        }

        const wsMetrics = document.getElementById("wsPolicyMetrics");
        const wsRuntime = data.ws_runtime || {};
        wsMetrics.innerHTML = `
          <div class="small">Enabled WS Policies: <strong>${fmt(wsRuntime.configured_enabled_venues)}</strong></div>
          <div class="small">Disabled WS Policies: <strong>${fmt(wsRuntime.configured_disabled_venues)}</strong></div>
          <div class="small">Active Ingestion Markets: <strong>${fmt(wsRuntime.active_markets)}</strong></div>
        `;
        const wsBody = document.querySelector("#wsPolicyTable tbody");
        wsBody.innerHTML = "";
        for (const row of tableSlice(data.ws_policies || [], 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}</td><td>${row.enabled ? "ON" : "OFF"}</td><td>${row.heartbeat_interval_seconds}</td><td>${row.stale_after_seconds}</td><td>${row.reconnect_backoff_seconds}/${row.max_backoff_seconds}</td><td>${fmt(row.jitter_pct)}</td><td>${row.max_consecutive_failures}</td><td>${row.updated_by}</td>`;
          wsBody.appendChild(tr);
        }

        const feedSlaBody = document.querySelector("#feedSlaTable tbody");
        feedSlaBody.innerHTML = "";
        for (const row of tableSlice(data.connector_feed_sla || [], 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}:${row.symbol}</td><td>${row.latency_ms ?? "-"}</td><td>${row.heartbeat_age_seconds ?? "-"}</td><td>${fmt(row.sequence_discontinuity_count)}</td><td>${fmt(row.drop_estimate_count)}</td><td>${fmt(row.ticks_24h)}</td>`;
          feedSlaBody.appendChild(tr);
        }

        const rlMetrics = document.getElementById("rateLimitPolicyMetrics");
        const rlRuntime = data.rate_limit_runtime || {};
        rlMetrics.innerHTML = `
          <div class="small">Enabled Rate Policies: <strong>${fmt(rlRuntime.configured_enabled_venues)}</strong></div>
          <div class="small">Disabled Rate Policies: <strong>${fmt(rlRuntime.configured_disabled_venues)}</strong></div>
          <div class="small">Avg Effective Poll (ms): <strong>${fmt(rlRuntime.avg_effective_poll_interval_ms)}</strong></div>
        `;
        const rlBody = document.querySelector("#rateLimitPolicyTable tbody");
        rlBody.innerHTML = "";
        for (const row of tableSlice(data.rate_limit_policies || [], 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.venue}</td><td>${row.enabled ? "ON" : "OFF"}</td><td>${row.min_poll_interval_ms}/${row.max_poll_interval_ms}</td><td>${fmt(row.backoff_multiplier)}</td><td>${row.recovery_step_ms}</td><td>${row.burst_cooldown_seconds}</td><td>${row.max_consecutive_rate_limit_hits}</td><td>${row.per_minute_soft_limit}</td><td>${row.updated_by}</td>`;
          rlBody.appendChild(tr);
        }

        const kafkaMetrics = document.getElementById("kafkaPolicyMetrics");
        const kafkaRuntime = data.kafka_runtime || {};
        kafkaMetrics.innerHTML = `
          <div class="small">Enabled Topic Policies: <strong>${fmt(kafkaRuntime.configured_enabled_topics)}</strong></div>
          <div class="small">Disabled Topic Policies: <strong>${fmt(kafkaRuntime.configured_disabled_topics)}</strong></div>
          <div class="small">Avg Target Partitions: <strong>${fmt(kafkaRuntime.avg_target_partitions)}</strong></div>
          <div class="small">Avg Retention (ms): <strong>${fmt(kafkaRuntime.avg_retention_ms)}</strong></div>
        `;
        const kafkaBody = document.querySelector("#kafkaTopicPolicyTable tbody");
        kafkaBody.innerHTML = "";
        for (const row of tableSlice(data.kafka_topic_policies || [], 40)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.topic_name}</td><td>${row.enabled ? "ON" : "OFF"}</td><td>${row.target_partitions}</td><td>${row.retention_ms}</td><td>${row.cleanup_policy}</td><td>${fmt(row.max_consumer_lag_messages)}</td><td>${fmt(row.max_consumer_lag_seconds)}</td><td>${fmt(row.min_insync_replicas)}</td><td>${row.updated_by}</td>`;
          kafkaBody.appendChild(tr);
        }

        const retentionBody = document.querySelector("#retentionPolicyTable tbody");
        retentionBody.innerHTML = "";
        for (const row of tableSlice(data.raw_lake_retention_policies || [], 20)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${row.environment}</td><td>${row.enabled ? "ON" : "OFF"}</td><td>${row.hot_retention_days}/${row.warm_retention_days}/${row.cold_retention_days}</td><td>${row.archive_tier}</td><td>${row.restore_sla_minutes}</td><td>${row.validation_interval_hours}</td><td>${row.updated_by}</td>`;
          retentionBody.appendChild(tr);
        }

        const restoreBody = document.querySelector("#restoreDrillTable tbody");
        restoreBody.innerHTML = "";
        for (const row of tableSlice(data.raw_lake_restore_drills || [], 30)) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td title="${row.drill_id}">${row.drill_id.slice(0, 8)}</td><td>${row.environment}</td><td>${row.window_from_ts || "-"} .. ${row.window_to_ts || "-"}</td><td>${fmt(row.object_count_checked)}/${fmt(row.row_count_checked)}</td><td>${row.checksum_match ? "MATCH" : "MISMATCH"}</td><td>${fmt(row.restore_duration_seconds)}</td><td>${row.status}</td>`;
          restoreBody.appendChild(tr);
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

      async function submitFailoverPolicy() {
        const payload = {
          venue: document.getElementById("fpVenue").value.trim(),
          enabled: document.getElementById("fpEnabled").value.trim().toLowerCase() === "true",
          primary_endpoint: document.getElementById("fpPrimary").value.trim(),
          secondary_endpoints: document.getElementById("fpSecondary").value.trim(),
          failure_threshold: Number(document.getElementById("fpFailureThreshold").value || 3),
          cooldown_seconds: Number(document.getElementById("fpCooldown").value || 60),
          reconnect_backoff_seconds: Number(document.getElementById("fpReconnectBackoff").value || 5),
          max_backoff_seconds: Number(document.getElementById("fpMaxBackoff").value || 120),
          request_timeout_seconds: Number(document.getElementById("fpRequestTimeout").value || 8),
          jitter_pct: Number(document.getElementById("fpJitterPct").value || 0.2),
          justification: document.getElementById("fpJustification").value.trim(),
        };
        const out = document.getElementById("fpResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/failover-policy", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated venue=${data.result?.venue || "-"} by ${data.result?.updated_by || "-"}`;
        await loadIngestion();
      }

      async function submitSessionPolicy() {
        const payload = {
          venue: document.getElementById("spVenue").value.trim(),
          enabled: document.getElementById("spEnabled").value.trim().toLowerCase() === "true",
          auth_mode: document.getElementById("spAuthMode").value.trim(),
          token_ttl_seconds: Number(document.getElementById("spTokenTtl").value || 1800),
          refresh_lead_seconds: Number(document.getElementById("spRefreshLead").value || 120),
          max_refresh_retries: Number(document.getElementById("spRetries").value || 2),
          lockout_cooldown_seconds: Number(document.getElementById("spCooldown").value || 60),
          classify_401: document.getElementById("spClass401").value.trim(),
          classify_403: document.getElementById("spClass403").value.trim(),
          classify_429: document.getElementById("spClass429").value.trim(),
          classify_5xx: document.getElementById("spClass5xx").value.trim(),
          justification: document.getElementById("spJustification").value.trim(),
        };
        const out = document.getElementById("spResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/session-policy", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated venue=${data.result?.venue || "-"} by ${data.result?.updated_by || "-"}`;
        await loadIngestion();
      }

      async function submitWsPolicy() {
        const payload = {
          venue: document.getElementById("wpVenue").value.trim(),
          enabled: document.getElementById("wpEnabled").value.trim().toLowerCase() === "true",
          heartbeat_interval_seconds: Number(document.getElementById("wpHeartbeat").value || 15),
          stale_after_seconds: Number(document.getElementById("wpStaleAfter").value || 45),
          reconnect_backoff_seconds: Number(document.getElementById("wpReconnectBackoff").value || 5),
          max_backoff_seconds: Number(document.getElementById("wpMaxBackoff").value || 120),
          jitter_pct: Number(document.getElementById("wpJitterPct").value || 0.2),
          max_consecutive_failures: Number(document.getElementById("wpMaxFailures").value || 5),
          justification: document.getElementById("wpJustification").value.trim(),
        };
        const out = document.getElementById("wpResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/ws-policy", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated venue=${data.result?.venue || "-"} by ${data.result?.updated_by || "-"}`;
        await loadIngestion();
      }

      async function submitRateLimitPolicy() {
        const payload = {
          venue: document.getElementById("rpVenue").value.trim(),
          enabled: document.getElementById("rpEnabled").value.trim().toLowerCase() === "true",
          min_poll_interval_ms: Number(document.getElementById("rpMinPollMs").value || 300),
          max_poll_interval_ms: Number(document.getElementById("rpMaxPollMs").value || 8000),
          backoff_multiplier: Number(document.getElementById("rpBackoffMultiplier").value || 1.6),
          recovery_step_ms: Number(document.getElementById("rpRecoveryStepMs").value || 100),
          burst_cooldown_seconds: Number(document.getElementById("rpBurstCooldown").value || 30),
          max_consecutive_rate_limit_hits: Number(document.getElementById("rpMax429Hits").value || 3),
          per_minute_soft_limit: Number(document.getElementById("rpSoftLimit").value || 120),
          justification: document.getElementById("rpJustification").value.trim(),
        };
        const out = document.getElementById("rpResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/rate-limit-policy", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated venue=${data.result?.venue || "-"} by ${data.result?.updated_by || "-"}`;
        await loadIngestion();
      }

      async function submitKafkaTopicPolicy() {
        const payload = {
          topic_name: document.getElementById("kpTopic").value.trim(),
          enabled: document.getElementById("kpEnabled").value.trim().toLowerCase() === "true",
          target_partitions: Number(document.getElementById("kpPartitions").value || 6),
          retention_ms: Number(document.getElementById("kpRetentionMs").value || -1),
          cleanup_policy: document.getElementById("kpCleanupPolicy").value.trim(),
          max_consumer_lag_messages: Number(document.getElementById("kpLagMessages").value || 10000),
          max_consumer_lag_seconds: Number(document.getElementById("kpLagSeconds").value || 60),
          min_insync_replicas: Number(document.getElementById("kpMinIsr").value || 1),
          justification: document.getElementById("kpJustification").value.trim(),
        };
        const out = document.getElementById("kpResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/kafka-topic-policy", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated topic=${data.result?.topic_name || "-"} by ${data.result?.updated_by || "-"}`;
        await loadIngestion();
      }

      async function buildReplayManifest() {
        const payload = {
          venue: document.getElementById("rmVenue").value.trim(),
          symbol: document.getElementById("rmSymbol").value.trim(),
          source_topic: document.getElementById("rmTopic").value.trim(),
          source_partition: Number(document.getElementById("rmPartition").value || 0),
          range_from_ts: document.getElementById("rmFromTs").value.trim(),
          range_to_ts: document.getElementById("rmToTs").value.trim(),
          justification: document.getElementById("rmJustification").value.trim(),
        };
        const out = document.getElementById("rmResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/raw-lake/replay-manifest", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Built manifest=${(data.result?.manifest_id || "-").slice(0, 8)} objects=${data.result?.object_count ?? "-"}`;
        await loadIngestion();
      }

      async function submitRawLakeRetentionPolicy() {
        const payload = {
          environment: document.getElementById("rtEnv").value.trim(),
          enabled: document.getElementById("rtEnabled").value.trim().toLowerCase() === "true",
          hot_retention_days: Number(document.getElementById("rtHotDays").value || 14),
          warm_retention_days: Number(document.getElementById("rtWarmDays").value || 90),
          cold_retention_days: Number(document.getElementById("rtColdDays").value || 365),
          archive_tier: document.getElementById("rtTier").value.trim(),
          restore_sla_minutes: Number(document.getElementById("rtRestoreSla").value || 120),
          validation_interval_hours: Number(document.getElementById("rtValidationHours").value || 24),
          justification: document.getElementById("rtJustification").value.trim(),
        };
        const out = document.getElementById("rtResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/raw-lake/retention-policy", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Updated env=${data.result?.environment || "-"} by ${data.result?.updated_by || "-"}`;
        await loadIngestion();
      }

      async function submitRawLakeRestoreDrill() {
        const payload = {
          environment: document.getElementById("rdEnv").value.trim(),
          window_from_ts: document.getElementById("rdFromTs").value.trim(),
          window_to_ts: document.getElementById("rdToTs").value.trim(),
          object_count_checked: Number(document.getElementById("rdObjects").value || 0),
          row_count_checked: Number(document.getElementById("rdRows").value || 0),
          checksum_match: document.getElementById("rdChecksum").value.trim().toLowerCase() === "true",
          restore_duration_seconds: Number(document.getElementById("rdDuration").value || 0),
          status: document.getElementById("rdStatus").value.trim(),
          notes: document.getElementById("rdNotes").value.trim(),
          justification: document.getElementById("rdJustification").value.trim(),
        };
        const out = document.getElementById("rdResult");
        out.textContent = "Submitting...";
        const res = await authedFetch("/api/v1/control-panel/ingestion/raw-lake/restore-drill", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          out.textContent = `Denied/Error: ${data.detail || "unknown error"}`;
          return;
        }
        out.textContent = `Logged drill=${(data.result?.drill_id || "-").slice(0, 8)} env=${data.result?.environment || "-"} status=${data.result?.status || "-"}`;
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
          tr.innerHTML = `<td>${row.venue}:${row.symbol} <button class="btn mini" onclick="openChartTab('${row.venue}','${row.symbol}','5m')">Chart Tab</button></td><td>${fmt(row.ohlcv_1m_count)} / ${fmt(row.ohlcv_target)}</td><td>${fmt(row.ohlcv_progress_pct)}%</td><td>${row.last_ohlcv_bucket || "-"}</td><td>${fmt(row.ticks_5m)}</td><td>${row.last_tick_ts || "-"}</td><td>${row.tick_lag_seconds ?? "-"}</td><td><span class="status ${kpiClass}">${kpiState}</span></td>`;
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
          tr.innerHTML = `<td>${row.venue}:${row.symbol} <button class="btn mini" onclick="openChartTab('${row.venue}','${row.symbol}','5m')">Chart Tab</button></td><td>${row.decisions_24h}</td><td>${fmt(row.avg_confidence)}</td><td>${row.violations_24h}</td><td><span class="status ${row.status === "healthy" ? "online" : "degraded"}">${row.status.toUpperCase()}</span></td>`;
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
          tr.innerHTML = `<td>${row.order_id}</td><td>${row.venue}:${row.symbol} <button class="btn mini" onclick="openChartTab('${row.venue}','${row.symbol}','5m')">Chart Tab</button></td><td>${row.side}</td><td>${row.status}</td><td>${fmt(row.requested_notional)}</td><td>${row.updated_at || "-"}</td>`;
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
        const tf = document.getElementById("cwTimeframe").value.trim() || "5m";

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
      function chartUrl(venue, symbol, timeframe = "5m") {
        const qs = new URLSearchParams({ venue, symbol, timeframe });
        return `/charting?${qs.toString()}`;
      }
      async function openChartTab(venue, symbol, timeframe = "5m") {
        const tf = (timeframe || document.getElementById("cwTimeframe").value.trim() || "5m").trim();
        const inputVenue = (venue || document.getElementById("cwVenue").value.trim()).trim().toLowerCase();
        const inputSymbol = (symbol || document.getElementById("cwSymbol").value.trim()).trim().toUpperCase();
        if (inputVenue && inputSymbol) {
          window.open(chartUrl(inputVenue, inputSymbol, tf), "_blank", "noopener");
          return;
        }
        const res = await authedFetch(`/api/v1/charting/markets/available?timeframe=${encodeURIComponent(tf)}`);
        if (!res.ok) {
          alert("Unable to load markets for chart launch.");
          return;
        }
        const data = await res.json();
        const first = (data.markets || [])[0];
        if (!first || !first.venue || !first.symbol) {
          alert("No markets available for chart launch.");
          return;
        }
        window.open(chartUrl(first.venue, first.symbol, tf), "_blank", "noopener");
      }
      window.openChartWorkbench = openChartWorkbench;
      window.openChartTab = openChartTab;
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
      document.getElementById("fpSubmitBtn").addEventListener("click", () => submitFailoverPolicy().catch(console.error));
      document.getElementById("spSubmitBtn").addEventListener("click", () => submitSessionPolicy().catch(console.error));
      document.getElementById("wpSubmitBtn").addEventListener("click", () => submitWsPolicy().catch(console.error));
      document.getElementById("rpSubmitBtn").addEventListener("click", () => submitRateLimitPolicy().catch(console.error));
      document.getElementById("kpSubmitBtn").addEventListener("click", () => submitKafkaTopicPolicy().catch(console.error));
      document.getElementById("rmBuildBtn").addEventListener("click", () => buildReplayManifest().catch(console.error));
      document.getElementById("rtSubmitBtn").addEventListener("click", () => submitRawLakeRetentionPolicy().catch(console.error));
      document.getElementById("rdSubmitBtn").addEventListener("click", () => submitRawLakeRestoreDrill().catch(console.error));
      document.getElementById("kpiLoadBtn").addEventListener("click", () => loadIngestionKpi().catch(console.error));
      document.getElementById("riskLimitsBtn").addEventListener("click", () => submitRiskLimits().catch(console.error));
      document.getElementById("killSwitchBtn").addEventListener("click", () => submitKillSwitch().catch(console.error));
      document.getElementById("executionCmdBtn").addEventListener("click", () => submitExecutionCommand().catch(console.error));
      document.getElementById("cwLoadBtn").addEventListener("click", () => loadChartingWorkbench().catch(console.error));
      document.getElementById("cwOpenTabBtn").addEventListener("click", () => openChartTab().catch(console.error));
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
