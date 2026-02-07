// ============================================================================
// OrbitalEngine.js -- Canvas Animation Engine for Orbital Greenhouse UI
// ============================================================================
// Drives the 3-zone fraud detection canvas:
//   Left   ~25%  Defense Grid   (scanning rings, pod analysis)
//   Middle ~40%  Transit Zone   (pods fly on Bezier curves)
//   Right  ~35%  Greenhouse     (cleared pods become growing plants)
//
// Depends on PixelSprites (global) for all drawing primitives.
// ============================================================================

const OrbitalEngine = (() => {
  const PS = typeof PixelSprites !== 'undefined' ? PixelSprites : null;
  const C  = PS ? PS.colors : {};

  const PETAL_COLORS = [
    '#e06060', '#9b6dff', '#ffd700', '#f0a0c0', '#7ec4cf', '#4ade80',
  ];

  const MAX_PODS   = 50;
  const MAX_PLANTS = 20;

  // Duration constants (seconds)
  const SPAWN_DUR   = 2.0;
  const SCAN_DUR    = 1.0;
  const FLAG_SHAKE  = 0.5;
  const FLAG_EXIT   = 1.0;
  const CLEAR_DUR   = 1.5;
  const LAND_DUR    = 0.6;
  const BRAIN_DUR   = 1.5;
  const PLANT_GROW  = 15.0;

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }

  function quadBezier(p0, p1, p2, t) {
    const u = 1 - t;
    return {
      x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x,
      y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y,
    };
  }

  function podSizeFromAmount(amount) {
    return clamp(Math.log10(amount / 100 + 1) * 6 + 6, 6, 32);
  }

  // --------------------------------------------------------------------------
  // OrbitalEngine class
  // --------------------------------------------------------------------------

  class OrbitalEngine {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx    = canvas.getContext('2d');

      // State
      this.pods         = new Map();
      this.plants       = [];
      this.brainPulses  = [];
      this.effects      = []; // landing bursts, sparkles
      this.stats        = { totalPods: 0, activePods: 0, threats: 0, cleared: 0, plants: 0 };
      this.time         = 0;
      this.lastFrame    = performance.now();
      this.scanAngle    = 0;
      this._rafId       = null;
      this._destroyed   = false;

      // Resize
      this._onResize = this._handleResize.bind(this);
      window.addEventListener('resize', this._onResize);
      this._handleResize();

      // Click detection
      this._onClick = this._handleClick.bind(this);
      this.canvas.addEventListener('click', this._onClick);

      // Start loop
      this._tick = this._tick.bind(this);
      this._rafId = requestAnimationFrame(this._tick);
    }

    // ======================================================================
    // Layout (recomputed on resize)
    // ======================================================================

    _computeLayout() {
      const w = this.canvas.width;
      const h = this.canvas.height;
      this.layout = {
        defenseX:     w * 0.22,
        defenseY:     h * 0.45,
        defenseR:     Math.min(w, h) * 0.18,
        greenhouseX:  w * 0.78,
        greenhouseY:  h * 0.55,
        greenhouseW:  w * 0.30,
        greenhouseH:  h * 0.45,
      };
    }

    _handleResize() {
      const parent = this.canvas.parentElement;
      if (parent) {
        this.canvas.width  = parent.clientWidth  || 800;
        this.canvas.height = parent.clientHeight || 500;
      }
      this._computeLayout();
    }

    // ======================================================================
    // Public API
    // ======================================================================

    addPod(txnId, amount, metadata) {
      if (this.pods.has(txnId)) return;
      const L  = this.layout;
      const sz = podSizeFromAmount(amount);

      // Spawn at left edge, random Y within defense grid vertical band
      const startX = -sz;
      const startY = L.defenseY + (Math.random() - 0.5) * L.defenseR * 1.6;

      // Bezier control point: arcs slightly up/down for organic feel
      const cp = {
        x: L.defenseX * 0.45,
        y: startY + (Math.random() - 0.5) * L.defenseR * 0.8,
      };

      const pod = {
        id:           txnId,
        x:            startX,
        y:            startY,
        targetX:      L.defenseX,
        targetY:      L.defenseY,
        size:         sz,
        state:        'spawning',
        type:         'neutral',
        spawnTime:    this.time,
        amount:       amount,
        metadata:     metadata || {},
        progress:     0,
        controlPoints: [cp],
        _prevX:       startX,
        _prevY:       startY,
      };

      this.pods.set(txnId, pod);
      this.stats.totalPods++;
      this._enforcePodLimit();
    }

    classifyPod(txnId, isThreat, riskScore) {
      const pod = this.pods.get(txnId);
      if (!pod || pod.state === 'done') return;

      pod.metadata.risk_score = riskScore;

      if (isThreat) {
        pod.type      = 'flagged';
        pod.state     = 'flagged';
        pod.progress  = 0;
        pod.spawnTime = this.time;
        this.stats.threats++;
      } else {
        pod.type      = 'clear';
        pod.state     = 'clearing';
        pod.progress  = 0;
        pod.spawnTime = this.time;

        // Bezier toward greenhouse
        const L  = this.layout;
        pod.targetX = L.greenhouseX;
        pod.targetY = L.greenhouseY + L.greenhouseH * 0.3;
        pod.controlPoints = [{
          x: (pod.x + pod.targetX) * 0.5,
          y: pod.y - L.defenseR * 0.5 * (0.5 + Math.random()),
        }];
        this.stats.cleared++;
      }
    }

    addPlant(patternName) {
      const L    = this.layout;
      const cols = 5;
      const idx  = this.plants.length % (cols * 4);
      const col  = idx % cols;
      const row  = Math.floor(idx / cols);
      const spacing = L.greenhouseW / (cols + 1);

      const plant = {
        x:           L.greenhouseX - L.greenhouseW * 0.40 + (col + 1) * spacing,
        y:           L.greenhouseY + L.greenhouseH * 0.35 - row * 28,
        stage:       0,
        startTime:   this.time,
        patternName: patternName || 'unknown',
        petalColor:  PETAL_COLORS[Math.floor(Math.random() * PETAL_COLORS.length)],
      };

      this.plants.push(plant);
      this.stats.plants = this.plants.length;
      this._enforcePlantLimit();
    }

    triggerBrainPulse() {
      const L = this.layout;
      this.brainPulses.push({
        x:         L.defenseX,
        y:         L.defenseY,
        startTime: this.time,
        maxRadius: L.defenseR * 1.8,
      });
    }

    getStats() {
      this.stats.activePods = 0;
      this.pods.forEach(p => { if (p.state !== 'done') this.stats.activePods++; });
      return { ...this.stats };
    }

    destroy() {
      this._destroyed = true;
      if (this._rafId) cancelAnimationFrame(this._rafId);
      window.removeEventListener('resize', this._onResize);
      this.canvas.removeEventListener('click', this._onClick);
    }

    // ======================================================================
    // Click detection
    // ======================================================================

    _handleClick(e) {
      const rect = this.canvas.getBoundingClientRect();
      const mx   = e.clientX - rect.left;
      const my   = e.clientY - rect.top;

      for (const [id, pod] of this.pods) {
        if (pod.state === 'done') continue;
        const dx = mx - pod.x;
        const dy = my - pod.y;
        if (dx * dx + dy * dy < (pod.size + 8) * (pod.size + 8)) {
          this.canvas.dispatchEvent(new CustomEvent('podClick', {
            detail: { txnId: id, pod: { ...pod } },
          }));
          return;
        }
      }
    }

    // ======================================================================
    // Limits
    // ======================================================================

    _enforcePodLimit() {
      if (this.pods.size <= MAX_PODS) return;
      for (const [id, pod] of this.pods) {
        if (pod.state === 'done') { this.pods.delete(id); }
        if (this.pods.size <= MAX_PODS) return;
      }
    }

    _enforcePlantLimit() {
      while (this.plants.length > MAX_PLANTS) this.plants.shift();
    }

    // ======================================================================
    // Animation loop
    // ======================================================================

    _tick(now) {
      if (this._destroyed) return;
      const dt = Math.min((now - this.lastFrame) / 1000, 0.1); // cap at 100ms
      this.lastFrame = now;
      this.time += dt;
      this.scanAngle += dt * 0.8;

      this._update(dt);
      this._draw();

      this._rafId = requestAnimationFrame(this._tick);
    }

    // ======================================================================
    // Update
    // ======================================================================

    _update(dt) {
      const L = this.layout;

      // --- Pods ---
      for (const [id, p] of this.pods) {
        p._prevX = p.x;
        p._prevY = p.y;

        const elapsed = this.time - p.spawnTime;

        switch (p.state) {
          case 'spawning': {
            p.progress = clamp(elapsed / SPAWN_DUR, 0, 1);
            const pt = quadBezier(
              { x: -p.size, y: p.y === p._prevY ? p.y : p._prevY },
              p.controlPoints[0],
              { x: L.defenseX, y: L.defenseY },
              p.progress
            );
            p.x = pt.x;
            p.y = pt.y;
            if (p.progress >= 1) {
              p.state     = 'scanning';
              p.spawnTime = this.time;
              p.progress  = 0;
            }
            break;
          }
          case 'scanning': {
            p.progress = clamp(elapsed / SCAN_DUR, 0, 1);
            // Small circular orbit around defense grid center
            const orbitR = L.defenseR * 0.3;
            const angle  = this.time * 2.5 + (parseInt(id, 36) % 100) * 0.5;
            p.x = L.defenseX + Math.cos(angle) * orbitR * (0.3 + p.progress * 0.7);
            p.y = L.defenseY + Math.sin(angle) * orbitR * 0.6 * (0.3 + p.progress * 0.7);
            // Stay scanning until classifyPod is called — no auto-transition
            break;
          }
          case 'flagged': {
            p.progress = clamp(elapsed / (FLAG_SHAKE + FLAG_EXIT), 0, 1);
            if (elapsed < FLAG_SHAKE) {
              // Shake in place
            } else {
              // Fly upward off-screen
              const exitT = (elapsed - FLAG_SHAKE) / FLAG_EXIT;
              p.y = p.y - dt * (300 + exitT * 400);
            }
            if (p.y < -p.size * 2) p.state = 'done';
            break;
          }
          case 'clearing': {
            p.progress = clamp(elapsed / CLEAR_DUR, 0, 1);
            const startPt = { x: L.defenseX, y: L.defenseY };
            const endPt   = { x: p.targetX, y: p.targetY };
            const pt = quadBezier(startPt, p.controlPoints[0], endPt, p.progress);
            p.x = pt.x;
            p.y = pt.y;
            if (p.progress >= 1) {
              p.state     = 'landing';
              p.spawnTime = this.time;
              p.progress  = 0;
            }
            break;
          }
          case 'landing': {
            p.progress = clamp(elapsed / LAND_DUR, 0, 1);
            if (p.progress >= 1) {
              // Convert to plant
              this.addPlant(p.metadata.fraud_type || p.metadata.txn_type || 'trade');
              // Landing burst effect
              this.effects.push({
                type:      'landing',
                x:         p.x,
                y:         p.y,
                startTime: this.time,
              });
              p.state = 'done';
            }
            break;
          }
          // 'done': no-op
        }
      }

      // --- Plants: advance growth stage ---
      for (const plant of this.plants) {
        const age = this.time - plant.startTime;
        plant.stage = clamp(Math.floor((age / PLANT_GROW) * 4), 0, 3);
      }

      // --- Clean up expired brain pulses and effects ---
      this.brainPulses = this.brainPulses.filter(
        bp => (this.time - bp.startTime) < BRAIN_DUR
      );
      this.effects = this.effects.filter(
        ef => (this.time - ef.startTime) < 1.5
      );
    }

    // ======================================================================
    // Draw
    // ======================================================================

    _draw() {
      if (!PS) return;
      const ctx = this.ctx;
      const w   = this.canvas.width;
      const h   = this.canvas.height;
      const L   = this.layout;

      // 1. Clear
      ctx.fillStyle = C.deepSpace;
      ctx.fillRect(0, 0, w, h);

      // 2. Background layers
      PS.drawStarfield(ctx, w, h, { time: this.time, starCount: 120 });
      PS.drawDotGrid(ctx, w, h, { spacing: 30, dotSize: 1 });

      // 3. Defense grid
      PS.drawDefenseGrid(ctx, L.defenseX, L.defenseY, L.defenseR, {
        scanAngle:  this.scanAngle,
        pulsePhase: this.time * 1.5,
        time:       this.time,
      });

      // 4. Greenhouse dome
      PS.drawGreenhouseDome(ctx, L.greenhouseX, L.greenhouseY, L.greenhouseW, L.greenhouseH, {
        time: this.time,
      });

      // 5. Plants
      const plantSize = clamp(Math.min(w, h) / 300, 1.2, 3);
      for (const plant of this.plants) {
        PS.drawPlantAtStage(ctx, plant.x, plant.y, plantSize, plant.stage, {
          time:       this.time,
          petalColor: plant.petalColor,
        });
      }

      // 6. Pods
      for (const [id, p] of this.pods) {
        if (p.state === 'done') continue;

        const velX = p.x - p._prevX;
        const velY = p.y - p._prevY;

        const shakeAmt = (p.state === 'flagged' && (this.time - p.spawnTime) < FLAG_SHAKE) ? 3 : 0;

        let drawType;
        switch (p.type) {
          case 'flagged': drawType = 'flagged'; break;
          case 'clear':   drawType = 'clear';   break;
          default:        drawType = 'neutral';  break;
        }

        // Trail
        if (Math.abs(velX) + Math.abs(velY) > 0.5) {
          let trailColor;
          switch (drawType) {
            case 'flagged': trailColor = C.threatRed;  break;
            case 'clear':   trailColor = C.clearGreen; break;
            default:        trailColor = C.podBlue;    break;
          }
          PS.drawPodTrail(ctx, p.x, p.y, velX, velY, trailColor, { trailLength: 10 });
        }

        // Pod sprite
        switch (drawType) {
          case 'flagged':
            PS.drawCargoPodFlagged(ctx, p.x, p.y, p.size / 16, {
              time:  this.time,
              shake: shakeAmt,
            });
            break;
          case 'clear':
            PS.drawCargoPodClear(ctx, p.x, p.y, p.size / 16, { glow: true });
            break;
          default:
            PS.drawCargoPodNeutral(ctx, p.x, p.y, p.size / 16, { glow: true });
            break;
        }

        // Status ring while scanning
        if (p.state === 'scanning') {
          PS.drawStatusRing(ctx, p.x, p.y, p.size + 4, C.amber, {
            lineWidth: 1.5,
            dashPhase: this.time * 40,
            dashed:    true,
          });
        }

        // Landing pulse
        if (p.state === 'landing') {
          PS.drawLandingBurst(ctx, p.x, p.y, p.progress, {
            maxRadius: 20,
            color:     C.clearGreen,
          });
        }
      }

      // 7. Brain pulse effects
      for (const bp of this.brainPulses) {
        const progress = clamp((this.time - bp.startTime) / BRAIN_DUR, 0, 1);
        PS.drawBrainPulse(ctx, bp.x, bp.y, progress, { maxRadius: bp.maxRadius });
      }

      // 8. Landing burst / sparkle effects
      for (const ef of this.effects) {
        const progress = clamp((this.time - ef.startTime) / 1.2, 0, 1);
        if (ef.type === 'landing') {
          PS.drawLandingBurst(ctx, ef.x, ef.y, progress, {
            maxRadius: 30,
            color:     C.clearGreen,
          });
          // Sparkles around landing
          for (let i = 0; i < 4; i++) {
            const angle = (i / 4) * Math.PI * 2 + this.time;
            const dist  = progress * 20;
            PS.drawSparkle(
              ctx,
              ef.x + Math.cos(angle) * dist,
              ef.y + Math.sin(angle) * dist,
              6, progress, C.clearGreen
            );
          }
        }
      }

      // 9. Scanlines overlay (CRT feel)
      PS.drawScanlines(ctx, w, h, { alpha: 0.03 });
    }
  }

  return OrbitalEngine;
})();

// Export for both browser (global) and Node/bundler (CommonJS)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OrbitalEngine;
}
