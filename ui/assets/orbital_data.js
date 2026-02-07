// ============================================================================
// OrbitalDataLayer.js -- SSE + REST bridge for Orbital Fortress UI
// ============================================================================
// Connects to the FastAPI backend via Server-Sent Events for real-time
// updates and REST for user actions. Bridges events to the OrbitalEngine
// canvas and updates DOM HUD/panel elements.
//
// Usage:
//   const data = new OrbitalDataLayer("http://localhost:8000", engine);
//   data.wireControls();            // after DOM ready
//   data.on("transaction", (e) => { ... });
//   await data.startSimulator({ tps: 2.5, fraud_rate: 0.35 });
//   data.destroy();
// ============================================================================

class OrbitalDataLayer {

  // --------------------------------------------------------------------------
  // Constructor
  // --------------------------------------------------------------------------
  constructor(backendUrl, engine) {
    this.url = backendUrl.replace(/\/+$/, '');
    this.engine = engine;

    // Internal event listeners: { eventType: Set<callback> }
    this._listeners = {};

    // Reconnect state
    this._sse = null;
    this._backoff = 1000;
    this._maxBackoff = 30000;
    this._reconnectTimer = null;
    this._destroyed = false;

    // TPS calculation ring buffer (timestamps of last 30 txns)
    this._txnTimestamps = [];

    // DOM update throttle
    this._domDirty = false;
    this._rafId = null;
    this._lastDomUpdate = 0;
    this._DOM_INTERVAL = 333; // ~3 updates/sec

    // Hydration guard — prevents double-hydration on reconnect
    this._hydrated = false;

    // Public state
    this.state = {
      connected: false,
      simulatorRunning: false,
      metrics: {
        total_txns: 0, flagged_txns: 0, cases_open: 0, cases_closed: 0,
        precision: null, recall: null, f1: null, model_version: 'missing',
      },
      recentTransactions: [],   // last 100
      openCases: new Map(),     // caseId => { txnId, riskScore, decision, fraudType }
      patterns: [],             // [{ name, type, confidence }]
    };

    this._connectSSE();
    this._startDomLoop();
  }

  // --------------------------------------------------------------------------
  // Event System
  // --------------------------------------------------------------------------
  on(type, cb)  { (this._listeners[type] ||= new Set()).add(cb); }
  off(type, cb) { this._listeners[type]?.delete(cb); }

  _emit(type, data) {
    if (this._listeners[type]) {
      for (const cb of this._listeners[type]) {
        try { cb(data); } catch (e) { console.error(`[OrbitalData] listener error (${type}):`, e); }
      }
    }
  }

  // --------------------------------------------------------------------------
  // SSE Connection
  // --------------------------------------------------------------------------
  _connectSSE() {
    if (this._destroyed) return;
    try {
      this._sse = new EventSource(`${this.url}/stream/events`);
    } catch (e) {
      console.warn('[OrbitalData] EventSource creation failed, retrying...', e);
      this._scheduleReconnect();
      return;
    }

    this._sse.onopen = () => {
      this._backoff = 1000;
      this.state.connected = true;
      this._emit('connection_change', { connected: true });
      this._markDomDirty();
    };

    this._sse.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        this._handleEvent(data);
      } catch (e) {
        console.warn('[OrbitalData] bad SSE payload:', evt.data);
      }
    };

    this._sse.onerror = () => {
      this.state.connected = false;
      this._emit('connection_change', { connected: false });
      this._markDomDirty();
      this._sse.close();
      this._scheduleReconnect();
    };
  }

  _scheduleReconnect() {
    if (this._destroyed) return;
    clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => {
      this._backoff = Math.min(this._backoff * 2, this._maxBackoff);
      this._connectSSE();
    }, this._backoff);
  }

  // --------------------------------------------------------------------------
  // Event Dispatch (SSE -> State + Engine + DOM)
  // --------------------------------------------------------------------------
  _handleEvent(ev) {
    switch (ev.type) {

      case 'transaction': {
        const t = {
          txnId: ev.txn_id,
          amount: ev.amount,
          riskScore: ev.risk_score,
          decision: ev.decision,
          timestamp: ev.timestamp,
          fraudType: ev.fraud_type,
          senderId: ev.sender_id,
          receiverId: ev.receiver_id,
          txnType: ev.txn_type,
        };
        // State
        this.state.recentTransactions.unshift(t);
        if (this.state.recentTransactions.length > 100) this.state.recentTransactions.length = 100;
        this.state.metrics.total_txns++;
        if (ev.decision === 'review' || ev.decision === 'block') this.state.metrics.flagged_txns++;

        // TPS ring
        this._txnTimestamps.push(Date.now());
        if (this._txnTimestamps.length > 30) this._txnTimestamps.shift();

        // Engine bridge
        if (this.engine?.addPod) {
          this.engine.addPod(ev.txn_id, ev.amount, {
            risk_score: ev.risk_score,
            decision: ev.decision,
            txn_type: ev.txn_type,
            sender_id: ev.sender_id,
            fraud_type: ev.fraud_type,
          });
        }

        // Delayed classification for visual effect
        if (this.engine?.classifyPod) {
          const id = ev.txn_id;
          const score = ev.risk_score;
          if (ev.decision === 'review' || ev.decision === 'block') {
            setTimeout(() => this.engine.classifyPod(id, true, score), 2000);
          } else {
            setTimeout(() => this.engine.classifyPod(id, false, score), 2500);
          }
        }

        this._emit('transaction', t);
        this._addFeedLine(
          ev.decision === 'block' ? 'danger' :
          ev.decision === 'review' ? 'primary' : 'scanner',
          `Pod ${ev.txn_id.slice(0, 8)} arrived -- ${ev.decision.toUpperCase()} ($${ev.amount.toFixed(2)}, risk ${(ev.risk_score * 100).toFixed(0)}%)`
        );
        break;
      }

      case 'case_created': {
        const c = {
          txnId: ev.txn_id,
          riskScore: ev.risk_score,
          decision: ev.decision,
          fraudType: ev.fraud_type || null,
        };
        // Use txn_id as case key until we get real case_id from label event
        const key = ev.case_id || ev.txn_id;
        // Dedup: skip if this case was already loaded by hydrateState()
        if (this.state.openCases.has(key)) break;
        this.state.openCases.set(key, c);
        this.state.metrics.cases_open = this.state.openCases.size;
        this._emit('case_created', { caseId: key, ...c });
        this._addFeedLine('danger', `Case opened for ${ev.txn_id.slice(0, 8)} -- risk ${(ev.risk_score * 100).toFixed(0)}%`);
        break;
      }

      case 'case_labeled': {
        if (ev.new_status === 'closed') {
          this.state.openCases.delete(ev.case_id);
          // Also try by txn_id in case stored that way
          this.state.openCases.delete(ev.txn_id);
          this.state.metrics.cases_open = this.state.openCases.size;
          this.state.metrics.cases_closed++;
        }
        this._emit('case_labeled', ev);
        const icon = ev.decision === 'fraud' ? 'danger' : 'secondary';
        this._addFeedLine(icon, `Case ${(ev.case_id || '').slice(0, 8)} labeled ${ev.decision.toUpperCase()}`);
        this._addLearningLine('scanner', `Pod ${(ev.txn_id || '').slice(0, 8)} ${ev.decision === 'fraud' ? 'confirmed threat' : 'cleared by operator'}`);
        break;
      }

      case 'retrain': {
        const oldPrec = this.state.metrics.precision;
        if (ev.metrics) {
          Object.assign(this.state.metrics, {
            precision: ev.metrics.precision ?? this.state.metrics.precision,
            recall: ev.metrics.recall ?? this.state.metrics.recall,
            f1: ev.metrics.f1 ?? this.state.metrics.f1,
          });
        }
        if (ev.model_version) this.state.metrics.model_version = ev.model_version;
        if (this.engine?.triggerBrainPulse) this.engine.triggerBrainPulse();
        this._showBrainPulse(oldPrec, this.state.metrics.precision);
        this._emit('retrain', ev);
        this._addFeedLine('secondary', `Defense retrain complete -- ${ev.model_version || 'new model'}`);
        this._addLearningLine('secondary', `Defense upgraded -- ${ev.model_version}, F1: ${(ev.metrics?.f1 ?? 0).toFixed(2)}`);
        break;
      }

      case 'pattern': {
        const p = { name: ev.name, type: ev.pattern_type, confidence: ev.confidence };
        this.state.patterns.unshift(p);
        if (this.state.patterns.length > 30) this.state.patterns.length = 30;
        if (this.engine?.addPlant) this.engine.addPlant(ev.name);
        this._emit('pattern', p);
        this._addFeedLine('secondary', `Pattern discovered: ${ev.name} (${(ev.confidence * 100).toFixed(0)}% confidence)`);
        this._addLearningLine('secondary', `New pattern: ${ev.name}`);
        break;
      }

      case 'simulator_started':
        this.state.simulatorRunning = true;
        this._addFeedLine('scanner', 'Simulator started');
        break;

      case 'simulator_stopped':
        this.state.simulatorRunning = false;
        this._addFeedLine('scanner', 'Simulator stopped');
        break;

      case 'simulator_configured':
        this._addFeedLine('scanner', `Simulator configured: ${ev.config?.tps} TPS, ${((ev.config?.fraud_rate || 0) * 100).toFixed(0)}% fraud`);
        break;

      case 'agent_decision': {
        const dt = ev.decision_type;
        if (dt === 'retrain_skipped') break;  // SILENT — no feed noise

        const reasoning = (ev.reasoning || '').slice(0, 80);

        if (dt === 'retrain_triggered') {
          this._addFeedLine('primary', `Guardian: RETRAIN TRIGGERED — ${reasoning}`);
          this._addLearningLine('primary', 'Guardian initiated retrain');
        } else if (dt === 'model_kept') {
          // Brain pulse ONLY on model_kept (not on triggered)
          if (ev.new_metrics) {
            Object.assign(this.state.metrics, {
              precision: ev.new_metrics.precision ?? this.state.metrics.precision,
              recall: ev.new_metrics.recall ?? this.state.metrics.recall,
              f1: ev.new_metrics.f1 ?? this.state.metrics.f1,
            });
            if (ev.new_version) this.state.metrics.model_version = ev.new_version;
            if (this.engine?.triggerBrainPulse) this.engine.triggerBrainPulse();
          }
          this._addFeedLine('secondary', `Guardian: MODEL KEPT — ${ev.new_version}, F1: ${(ev.new_metrics?.f1 ?? 0).toFixed(2)}`);
        } else if (dt === 'model_rolled_back') {
          if (ev.old_version) this.state.metrics.model_version = ev.old_version;
          this._addFeedLine('danger', `Guardian: ROLLBACK — ${reasoning}`);
          this._addLearningLine('danger', `Defense reverted to ${ev.old_version}`);
        }

        this._emit('agent_decision', ev);
        break;
      }

      case 'heartbeat':
      case 'connected':
        break;

      default:
        console.debug('[OrbitalData] unknown event:', ev.type);
    }

    this._markDomDirty();
  }

  // --------------------------------------------------------------------------
  // REST Actions
  // --------------------------------------------------------------------------
  async _post(path, body) {
    const resp = await fetch(`${this.url}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body != null ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`POST ${path} -> ${resp.status}`);
    return resp.json();
  }

  async _get(path) {
    const resp = await fetch(`${this.url}${path}`);
    if (!resp.ok) throw new Error(`GET ${path} -> ${resp.status}`);
    return resp.json();
  }

  async startSimulator(config) {
    const body = config ? {
      tps: config.tps ?? 1.0,
      fraud_rate: config.fraud_rate ?? 0.10,
      fraud_types: config.fraud_types ?? undefined,
    } : {};
    const r = await this._post('/simulator/start', body);
    this.state.simulatorRunning = true;
    return r;
  }

  async stopSimulator() {
    const r = await this._post('/simulator/stop', {});
    this.state.simulatorRunning = false;
    return r;
  }

  async configureSimulator(config) {
    const payload = {
      tps: config.tps ?? 1.0,
      fraud_rate: config.fraud_rate ?? 0.10,
      fraud_types: config.fraud_types ?? undefined,
    };
    const result = await this._post('/simulator/configure', payload);
    try { localStorage.setItem('orbital_sim_config', JSON.stringify(payload)); } catch (e) { /* Safari private browsing */ }
    return result;
  }

  async getSimulatorStatus() {
    const s = await this._get('/simulator/status');
    this.state.simulatorRunning = s.running;
    return s;
  }

  async labelCase(caseId, decision) {
    return this._post(`/cases/${caseId}/label`, {
      decision,
      labeled_by: 'demo_analyst',
    });
  }

  async triggerRetrain()  { return this._post('/retrain', {}); }
  async triggerMining()   { return this._post('/mine-patterns', {}); }
  async getMetrics()      { const m = await this._get('/metrics'); Object.assign(this.state.metrics, m); this._markDomDirty(); return m; }
  async getPatterns()     { return this._get('/patterns?limit=15'); }
  async getCases(status, limit) { return this._get(`/cases?${status ? `status=${status}&` : ''}limit=${limit || 20}`); }

  // --------------------------------------------------------------------------
  // State Hydration (restore UI from backend on load/reconnect)
  // --------------------------------------------------------------------------

  /**
   * Fetch persisted state from backend REST endpoints and populate the
   * in-memory state + DOM so the UI shows existing data immediately after
   * page load or SSE reconnect.
   *
   * Safe to call multiple times — the _hydrated guard prevents duplicate work.
   */
  async hydrateState() {
    if (this._hydrated) return;
    this._hydrated = true;

    // Run fetches in parallel for speed; each is wrapped in its own
    // try/catch so one failing endpoint doesn't break the others.
    const [casesResult, txnsResult, simResult, patternsResult] = await Promise.allSettled([
      this._get('/cases?status=open&limit=20'),
      this._get('/transactions?limit=50'),
      this._get('/simulator/status'),
      this._get('/patterns?limit=15'),
    ]);

    // --- 1. Open cases -> inspection queue ---
    try {
      if (casesResult.status === 'fulfilled') {
        const cases = casesResult.value;
        for (const c of cases) {
          const key = c.case_id || c.txn_id;
          if (!this.state.openCases.has(key)) {
            this.state.openCases.set(key, {
              txnId: c.txn_id,
              riskScore: c.risk_score,
              decision: c.priority === 'high' ? 'block' : 'review',
              fraudType: null,
            });
          }
        }
        this.state.metrics.cases_open = this.state.openCases.size;
      }
    } catch (e) {
      console.warn('[OrbitalData] hydrateState: cases failed', e);
    }

    // --- 2. Recent transactions -> event feed + satellite orbits ---
    try {
      if (txnsResult.status === 'fulfilled') {
        const txns = txnsResult.value;
        // Transactions come newest-first from the API; reverse so we
        // populate oldest-first and the newest end up at the top of the
        // feed (prepend order).
        const ordered = [...txns].reverse();
        let approvedCount = 0;

        for (const t of ordered) {
          // Populate state (avoid duplicates by txn_id)
          const already = this.state.recentTransactions.some(r => r.txnId === t.txn_id);
          if (!already) {
            this.state.recentTransactions.unshift({
              txnId: t.txn_id,
              amount: t.amount,
              riskScore: t.risk_score,
              decision: t.decision,
              timestamp: t.timestamp,
              fraudType: null,
              senderId: t.sender_id,
              receiverId: t.receiver_id,
              txnType: t.txn_type,
            });
          }

          // Add feed line for each
          const color = t.decision === 'block' ? 'danger' :
                        t.decision === 'review' ? 'primary' : 'scanner';
          this._addFeedLine(
            color,
            `Pod ${t.txn_id.slice(0, 8)} -- ${(t.decision || 'approve').toUpperCase()} ($${Number(t.amount).toFixed(2)}, risk ${Math.round((t.risk_score || 0) * 100)}%)`
          );

          // Rebuild satellite orbits for approved txns
          if (t.decision === 'approve' || !t.decision) {
            approvedCount++;
          }
        }

        // Cap state buffer
        if (this.state.recentTransactions.length > 100) {
          this.state.recentTransactions.length = 100;
        }

        // Add satellites in bulk (engine may not exist yet)
        if (this.engine?.addSatellite) {
          for (let i = 0; i < approvedCount; i++) {
            this.engine.addSatellite();
          }
        }
      }
    } catch (e) {
      console.warn('[OrbitalData] hydrateState: transactions failed', e);
    }

    // --- 3. Simulator config -> sync DOM controls ---
    try {
      if (simResult.status === 'fulfilled') {
        const config = simResult.value;
        this.state.simulatorRunning = config.running;

        // Fraud rate slider
        const frSlider = document.querySelector('#fraud-rate');
        const frVal = document.querySelector('#fraud-rate-val');
        if (frSlider && config.fraud_rate != null) {
          frSlider.value = Math.round(config.fraud_rate * 100);
          if (frVal) frVal.textContent = `${Math.round(config.fraud_rate * 100)}%`;
        }

        // TPS slider
        const tpsSlider = document.querySelector('#tps');
        const tpsVal = document.querySelector('#tps-val');
        if (tpsSlider && config.tps != null) {
          tpsSlider.value = config.tps;
          if (tpsVal) tpsVal.textContent = config.tps;
        }

        // Fraud type checkboxes
        if (config.fraud_types) {
          for (const [ft, on] of Object.entries(config.fraud_types)) {
            const cb = document.querySelector(`[data-fraud="${ft}"]`);
            if (cb) cb.checked = !!on;
          }
        }

        // Start/Stop button visibility
        const btnStart = document.querySelector('#btn-start');
        const btnStop = document.querySelector('#btn-stop');
        if (config.running) {
          if (btnStart) btnStart.style.display = 'none';
          if (btnStop) btnStop.style.display = '';
        } else {
          if (btnStart) btnStart.style.display = '';
          if (btnStop) btnStop.style.display = 'none';
        }
      }
    } catch (e) {
      console.warn('[OrbitalData] hydrateState: simulator config failed', e);
    }

    // --- 4. Patterns -> state + panel ---
    try {
      if (patternsResult.status === 'fulfilled') {
        const patterns = patternsResult.value;
        for (const p of patterns) {
          const name = p.name;
          // Dedup by name
          if (!this.state.patterns.some(existing => existing.name === name)) {
            this.state.patterns.push({
              name: p.name,
              type: p.pattern_type,
              confidence: p.confidence,
            });
          }
        }
        if (this.state.patterns.length > 30) this.state.patterns.length = 30;
      }
    } catch (e) {
      console.warn('[OrbitalData] hydrateState: patterns failed', e);
    }

    // Force immediate DOM rebuild (don't wait for next rAF tick)
    this._updateDOM();
    this._markDomDirty();
    console.log('[OrbitalData] State hydrated:', {
      cases: this.state.openCases.size,
      transactions: this.state.recentTransactions.length,
      patterns: this.state.patterns.length,
      simulatorRunning: this.state.simulatorRunning,
    });
  }

  // --------------------------------------------------------------------------
  // DOM Update Loop (throttled via rAF)
  // --------------------------------------------------------------------------
  _markDomDirty() { this._domDirty = true; }

  _startDomLoop() {
    const tick = () => {
      if (this._destroyed) return;
      const now = performance.now();
      if (this._domDirty && now - this._lastDomUpdate >= this._DOM_INTERVAL) {
        this._domDirty = false;
        this._lastDomUpdate = now;
        this._updateDOM();
      }
      this._rafId = requestAnimationFrame(tick);
    };
    this._rafId = requestAnimationFrame(tick);
  }

  _updateDOM() {
    const m = this.state.metrics;

    // --- HUD ---
    this._setText('#hud-pods',    m.total_txns);
    this._setText('#hud-threats', m.flagged_txns);
    this._setText('#hud-health',  m.precision != null ? `${(m.precision * 100).toFixed(0)}%` : '--');
    this._setText('#hud-version', m.model_version);

    const statusEl = document.querySelector('#hud-status');
    if (statusEl) {
      statusEl.textContent = this.state.connected ? 'ONLINE' : 'RECONNECTING';
      statusEl.className = this.state.connected
        ? 'text-secondary glow-green'
        : 'text-danger glow-red';
    }

    // --- Left panel metrics ---
    this._setText('#metric-tps', `${this._computeTPS().toFixed(1)} TPS`);

    // Show "--" when no labels exist (precision/recall are null)
    const hasLabels = m.precision != null && m.precision !== undefined;

    // False positive rate: flagged_not_fraud / total_flagged (approx from metrics)
    const fpr = hasLabels ? ((1 - m.precision) * 100) : 0;
    this._setText('#metric-fpr', hasLabels ? `${fpr.toFixed(1)}%` : '--');
    this._setBar('#bar-fpr', hasLabels ? fpr : 0);

    const prec = hasLabels ? m.precision * 100 : 0;
    this._setText('#metric-prec', hasLabels ? `${prec.toFixed(0)}%` : '--');
    this._setBar('#bar-prec', hasLabels ? prec : 0);

    const hasRecall = m.recall != null && m.recall !== undefined;
    const rec = hasRecall ? m.recall * 100 : 0;
    this._setText('#metric-recall', hasRecall ? `${rec.toFixed(0)}%` : '--');
    this._setBar('#bar-recall', hasRecall ? rec : 0);

    // --- Right panel: Inspection Queue ---
    this._rebuildQueue();

    // --- Right panel: Patterns ---
    this._rebuildPatterns();
  }

  _setText(sel, val) {
    const el = document.querySelector(sel);
    if (el) el.textContent = val;
  }

  _setBar(sel, pct) {
    const el = document.querySelector(sel);
    if (el) el.style.width = `${Math.min(100, Math.max(0, pct))}%`;
  }

  _computeTPS() {
    const ts = this._txnTimestamps;
    if (ts.length < 2) return 0;
    const span = (ts[ts.length - 1] - ts[0]) / 1000;
    return span > 0 ? (ts.length - 1) / span : 0;
  }

  // --------------------------------------------------------------------------
  // DOM Builders
  // --------------------------------------------------------------------------
  _rebuildQueue() {
    const container = document.querySelector('#inspection-queue');
    if (!container) return;

    const items = [...this.state.openCases.entries()].slice(0, 5);

    // Change detection: only rebuild if queue content actually changed
    const newKey = items.map(([id, c]) => `${id}:${c.riskScore}`).join('|');
    if (this._lastQueueKey === newKey) return;
    this._lastQueueKey = newKey;

    container.innerHTML = '';

    for (const [caseId, c] of items) {
      const pct = Math.round((c.riskScore || 0) * 100);
      const color = pct >= 80 ? 'danger' : 'primary';
      const barClass = pct >= 80 ? 'bar-red' : 'bar-amber';
      const label = c.fraudType || c.decision || 'Review';

      const div = document.createElement('div');
      div.className = 'queue-item';
      div.dataset.pod = c.txnId || caseId;
      div.innerHTML = `
        <div class="flex justify-between items-center mb-1">
          <span class="pixel-text text-xs text-${color}">${this._esc((c.txnId || caseId).slice(0, 8))}</span>
          <span class="text-xs text-${color} font-bold">${pct}</span>
        </div>
        <div class="bar-track mb-1.5"><div class="bar-fill ${barClass}" style="width:${pct}%"></div></div>
        <div class="text-xs text-white/40 mb-2">${this._esc(this._capitalize(label))}</div>
        <div class="flex gap-2">
          <button class="btn-action" data-action="clear" data-case="${this._esc(caseId)}">&#9989; CLEAR</button>
          <button class="btn-action" data-action="investigate" data-case="${this._esc(caseId)}">&#128270; INVESTIGATE</button>
        </div>`;
      container.appendChild(div);
    }

    // Wire queue buttons
    container.querySelectorAll('[data-action="clear"]').forEach(btn => {
      btn.onclick = async () => {
        const caseId = btn.dataset.case;
        btn.disabled = true;
        btn.textContent = '...';
        try {
          await this.labelCase(caseId, 'not_fraud');
          btn.textContent = '\u2713 Cleared';
          btn.style.color = '#4ade80';
          btn.style.borderColor = '#4ade80';
          // Remove from local state
          this.state.openCases.delete(caseId);
          this.state.metrics.cases_open = this.state.openCases.size;
          this.state.metrics.cases_closed++;
          // Rebuild queue after brief flash
          setTimeout(() => this._rebuildQueue(), 800);
        } catch (e) {
          btn.textContent = '\u2715 Error';
          btn.style.color = '#ef4444';
          setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '\u2705 CLEAR';
            btn.style.color = '';
            btn.style.borderColor = '';
          }, 1500);
        }
      };
    });
    container.querySelectorAll('[data-action="investigate"]').forEach(btn => {
      btn.onclick = async () => {
        const caseId = btn.dataset.case;
        btn.disabled = true;
        btn.textContent = 'Analyzing...';
        try {
          const result = await this._get(`/cases/${caseId}/explain`);
          this._showExplanation(caseId, result);
          btn.textContent = '\u2713 Done';
          btn.style.color = '#7ec4cf';
          setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '\uD83D\uDD0E INVESTIGATE';
            btn.style.color = '';
          }, 2000);
        } catch (e) {
          btn.textContent = '\u2715 Failed';
          btn.style.color = '#ef4444';
          setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '\uD83D\uDD0E INVESTIGATE';
            btn.style.color = '';
          }, 1500);
        }
      };
    });
  }

  _rebuildPatterns() {
    const container = document.querySelector('#pattern-list');
    if (!container) return;

    const items = this.state.patterns.slice(0, 15);

    if (items.length === 0) {
      // Show fallback only if not already showing it
      if (!container.querySelector('.pattern-empty')) {
        container.innerHTML = '<div class="pattern-empty text-xs text-white/30 p-2">No patterns discovered yet</div>';
      }
      return;
    }

    container.innerHTML = '';

    const icons = {
      graph: '&#127754;', velocity: '&#9889;', statistical: '&#128202;',
      cluster: '&#128260;', default: '&#128737;',
    };

    for (const p of items) {
      const icon = icons[p.type] || icons.default;
      const conf = Math.round((p.confidence || 0) * 100);
      const cls = conf >= 80 ? 'text-secondary' : 'text-primary';
      const div = document.createElement('div');
      div.className = 'pattern-card';
      div.innerHTML = `
        <span class="text-lg flex-none w-6 text-center">${icon}</span>
        <span class="flex-1">${this._esc(p.name)}</span>
        <span class="${cls} text-xs font-bold">${conf}%</span>`;
      container.appendChild(div);
    }
  }

  // --------------------------------------------------------------------------
  // Feed & Log Helpers
  // --------------------------------------------------------------------------
  _addFeedLine(color, text) {
    const container = document.querySelector('#event-lines');
    if (!container) return;
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
    const div = document.createElement('div');
    div.className = `feed-line text-${color}`;
    div.textContent = `[${ts}] ${text}`;
    container.prepend(div);
    while (container.children.length > 30) container.lastChild.remove();
  }

  _addLearningLine(color, text) {
    const inner = document.querySelector('#learning-log .p-2');
    if (!inner) return;
    const div = document.createElement('div');
    div.className = `feed-line text-${color}`;
    div.textContent = text;
    inner.prepend(div);
    while (inner.children.length > 20) inner.lastChild.remove();
  }

  _showBrainPulse(oldPrec, newPrec) {
    const el = document.querySelector('#brain-pulse');
    if (!el) return;
    this._setText('#brain-from', oldPrec != null ? `${(oldPrec * 100).toFixed(0)}%` : '--');
    this._setText('#brain-to',   newPrec != null ? `${(newPrec * 100).toFixed(0)}%` : '--');
    el.style.display = 'flex';
    clearTimeout(this._brainTimer);
    this._brainTimer = setTimeout(() => { el.style.display = 'none'; }, 4000);
  }

  _showExplanation(caseId, data) {
    const card = document.querySelector('#alert-card');
    if (!card) return;

    this._setText('#alert-pod', (data.txn_id || caseId).slice(0, 12));
    this._setText('#alert-pattern', data.summary || 'AI Analysis');

    const score = data.risk_score || data.confidence;
    this._setText('#alert-risk', score != null ? `${(score * 100).toFixed(0)}%` : '--');

    // Build detail text from available fields
    let detail = '';
    if (data.recommendation) detail += data.recommendation;
    if (data.behavioral_analysis) detail += (detail ? ' | ' : '') + data.behavioral_analysis;
    if (data.risk_factors && data.risk_factors.length) {
      detail += (detail ? ' | ' : '') + 'Factors: ' + data.risk_factors.slice(0, 3).join(', ');
    }
    this._setText('#alert-detail', detail || 'No additional details');

    this._setText('#alert-conf', data.agent || 'fraud-agent');

    card.style.display = 'block';

    // Auto-hide after 15 seconds
    clearTimeout(this._alertTimer);
    this._alertTimer = setTimeout(() => { card.style.display = 'none'; }, 15000);
  }

  _capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : ''; }

  /** Escape HTML special characters to prevent XSS via innerHTML. */
  _esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#x27;');
  }

  // --------------------------------------------------------------------------
  // Button Wiring (call after DOM ready)
  // --------------------------------------------------------------------------
  wireControls() {
    // Restore saved simulator config from localStorage before wiring listeners
    this.restoreSimConfig();

    // Start / Stop (toggle visibility)
    const btnStart = document.querySelector('#btn-start');
    const btnStop  = document.querySelector('#btn-stop');
    btnStart?.addEventListener('click', () => {
      this.startSimulator(this._readSimConfig())
        .then(() => { btnStart.style.display = 'none'; btnStop.style.display = ''; })
        .catch(console.error);
    });
    btnStop?.addEventListener('click', () => {
      this.stopSimulator()
        .then(() => { btnStop.style.display = 'none'; btnStart.style.display = ''; })
        .catch(console.error);
    });

    // Fraud rate slider
    const frSlider = document.querySelector('#fraud-rate');
    const frVal    = document.querySelector('#fraud-rate-val');
    if (frSlider) {
      frSlider.addEventListener('input', () => {
        if (frVal) frVal.textContent = `${frSlider.value}%`;
      });
      frSlider.addEventListener('change', () => {
        this.configureSimulator(this._readSimConfig()).catch(console.error);
      });
    }

    // TPS slider
    const tpsSlider = document.querySelector('#tps');
    const tpsVal    = document.querySelector('#tps-val');
    if (tpsSlider) {
      tpsSlider.addEventListener('input', () => {
        if (tpsVal) tpsVal.textContent = tpsSlider.value;
      });
      tpsSlider.addEventListener('change', () => {
        this.configureSimulator(this._readSimConfig()).catch(console.error);
      });
    }

    // Scenario presets
    const PRESETS = {
      normal: { tps: 2.0, fraud_rate: 0.10, fraud_types: { wash_trading: true, unauthorized_transfer: true, bonus_abuse: false, structuring: false, velocity_abuse: true } },
      mixed:  { tps: 3.0, fraud_rate: 0.35, fraud_types: { wash_trading: true, unauthorized_transfer: true, bonus_abuse: true,  structuring: true,  velocity_abuse: true } },
      storm:  { tps: 5.0, fraud_rate: 0.55, fraud_types: { wash_trading: true, unauthorized_transfer: true, bonus_abuse: true,  structuring: true,  velocity_abuse: true } },
    };

    document.querySelectorAll('[data-scenario]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-scenario]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const preset = PRESETS[btn.dataset.scenario];
        if (!preset) return;
        // Sync sliders
        if (frSlider) { frSlider.value = preset.fraud_rate * 100; if (frVal) frVal.textContent = `${Math.round(preset.fraud_rate * 100)}%`; }
        if (tpsSlider) { tpsSlider.value = preset.tps; if (tpsVal) tpsVal.textContent = preset.tps; }
        // Sync checkboxes
        for (const [ft, on] of Object.entries(preset.fraud_types)) {
          const cb = document.querySelector(`[data-fraud="${ft}"]`);
          if (cb) cb.checked = on;
        }
        this.configureSimulator(preset).catch(console.error);
      });
    });

    // Fraud type checkboxes
    document.querySelectorAll('[data-fraud]').forEach(cb => {
      cb.addEventListener('change', () => {
        this.configureSimulator(this._readSimConfig()).catch(console.error);
      });
    });
  }

  /** Read current slider + checkbox state from the DOM into a config object. */
  _readSimConfig() {
    const tps = parseFloat(document.querySelector('#tps')?.value) || 1.0;
    const fraud_rate = (parseFloat(document.querySelector('#fraud-rate')?.value) || 10) / 100;
    const fraud_types = {};
    document.querySelectorAll('[data-fraud]').forEach(cb => {
      fraud_types[cb.dataset.fraud] = cb.checked;
    });
    return { tps, fraud_rate, fraud_types };
  }

  /** Restore simulator config from localStorage into DOM controls (no backend POST). */
  restoreSimConfig() {
    try {
      const raw = localStorage.getItem('orbital_sim_config');
      if (!raw) return;
      const config = JSON.parse(raw);

      // Restore TPS slider
      const tpsSlider = document.querySelector('#tps');
      const tpsVal    = document.querySelector('#tps-val');
      if (tpsSlider && config.tps != null) {
        tpsSlider.value = config.tps;
        if (tpsVal) tpsVal.textContent = config.tps;
      }

      // Restore fraud rate slider
      const frSlider = document.querySelector('#fraud-rate');
      const frVal    = document.querySelector('#fraud-rate-val');
      if (frSlider && config.fraud_rate != null) {
        frSlider.value = Math.round(config.fraud_rate * 100);
        if (frVal) frVal.textContent = `${Math.round(config.fraud_rate * 100)}%`;
      }

      // Restore fraud type checkboxes
      if (config.fraud_types) {
        for (const [ft, on] of Object.entries(config.fraud_types)) {
          const cb = document.querySelector(`[data-fraud="${ft}"]`);
          if (cb) cb.checked = !!on;
        }
      }
    } catch (e) { /* corrupt or unavailable localStorage */ }
  }

  // --------------------------------------------------------------------------
  // Cleanup
  // --------------------------------------------------------------------------
  destroy() {
    this._destroyed = true;
    clearTimeout(this._reconnectTimer);
    clearTimeout(this._brainTimer);
    clearTimeout(this._alertTimer);
    if (this._rafId) cancelAnimationFrame(this._rafId);
    if (this._sse) { this._sse.close(); this._sse = null; }
    this._listeners = {};
  }
}

// Export for browser (global) and Node (CommonJS)
if (typeof window !== 'undefined') window.OrbitalDataLayer = OrbitalDataLayer;
if (typeof module !== 'undefined' && module.exports) module.exports = OrbitalDataLayer;
