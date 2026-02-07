// ============================================================================
// OrbitalEngine.js -- Canvas Animation Engine for Orbital Fortress UI
// ============================================================================
// Drives the 3-zone fraud detection canvas:
//   Left   ~25%  Defense Grid   (scanning rings, pod analysis)
//   Middle ~40%  Transit Zone   (pods fly on Bezier curves)
//   Right  ~35%  Earth          (cleared pods become orbiting satellites)
//
// Depends on PixelSprites (global) for all drawing primitives.
// ============================================================================

const OrbitalEngine = (() => {
  const PS = typeof PixelSprites !== 'undefined' ? PixelSprites : null;
  const C  = PS ? PS.colors : {};

  const SHIELD_COLORS = [
    '#00e5ff', '#1e88e5', '#80f0ff', '#40c4ff', '#7ec4cf', '#4ade80',
  ];

  const MAX_PODS       = 50;
  const MAX_SATELLITES = 30;

  // Duration constants (seconds)
  const SPAWN_DUR   = 2.0;
  const SCAN_DUR    = 1.0;
  const FLAG_SHAKE  = 0.5;
  const FLAG_EXIT   = 1.0;
  const CLEAR_DUR   = 1.5;
  const LAND_DUR    = 0.6;
  const BRAIN_DUR   = 1.5;
  const MERGE_DUR   = 1.5;

  // Orbit bands around Earth: radius multiplier and angular speed (rad/s)
  const ORBIT_BANDS = [
    { radius: 1.4, speed: 0.6  },  // closest, fastest
    { radius: 1.8, speed: 0.45 },
    { radius: 2.2, speed: 0.35 },
    { radius: 2.6, speed: 0.25 },  // farthest, slowest
  ];

  const MERGE_THRESHOLD = 5;  // satellites of same generation to trigger merge
  const MAX_GENERATION  = 4;  // gen 4 satellites never combine

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
      this.satellites   = [];
      this.brainPulses  = [];
      this.effects      = []; // landing bursts, sparkles, merge flashes
      this.stats        = { totalPods: 0, activePods: 0, threats: 0, cleared: 0, plants: 0 };
      this.time         = 0;
      this.lastFrame    = performance.now();
      this.scanAngle    = 0;
      this._rafId       = null;
      this._destroyed   = false;
      this._canvasWidth = canvas.width;

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
        defenseX:    w * 0.22,
        defenseY:    h * 0.45,
        defenseR:    Math.min(w, h) * 0.18,
        fortressX:   w * 0.78,
        fortressY:   h * 0.55,
        fortressW:   w * 0.30,
        fortressH:   h * 0.45,
        earthRadius: Math.min(w, h) * 0.14,
      };
    }

    _handleResize() {
      const parent = this.canvas.parentElement;
      if (parent) {
        this.canvas.width  = parent.clientWidth  || 800;
        this.canvas.height = parent.clientHeight || 500;
      }
      this._canvasWidth = this.canvas.width;
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

        // Bezier toward Earth
        const L  = this.layout;
        pod.targetX = L.fortressX;
        pod.targetY = L.fortressY + L.earthRadius * 0.5;
        pod.controlPoints = [{
          x: (pod.x + pod.targetX) * 0.5,
          y: pod.y - L.defenseR * 0.5 * (0.5 + Math.random()),
        }];
        this.stats.cleared++;
      }
    }

    addSatellite() {
      const L = this.layout;

      // Find orbit band with fewest satellites
      const bandCounts = ORBIT_BANDS.map(() => 0);
      for (const sat of this.satellites) {
        if (!sat.merging) bandCounts[sat.bandIndex]++;
      }
      let bestBand = 0;
      let bestCount = bandCounts[0];
      for (let i = 1; i < ORBIT_BANDS.length; i++) {
        if (bandCounts[i] < bestCount) {
          bestCount = bandCounts[i];
          bestBand  = i;
        }
      }

      const band = ORBIT_BANDS[bestBand];
      const satellite = {
        orbitRadius: band.radius * L.earthRadius,
        orbitAngle:  Math.random() * Math.PI * 2,
        orbitSpeed:  band.speed,
        generation:  0,
        startTime:   this.time,
        merging:     false,
        mergeTarget: null,
        mergeProgress: 0,
        bandIndex:   bestBand,
      };

      this.satellites.push(satellite);
      this.stats.plants = this.satellites.length;
      this._enforceSatelliteLimit();
    }

    // Backward-compat aliases (called by OrbitalDataLayer)
    addDefense(patternName) { return this.addSatellite(); }
    addPlant(patternName)   { return this.addSatellite(); }

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
      this.stats.plants = this.satellites.length;
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

    _enforceSatelliteLimit() {
      while (this.satellites.length > MAX_SATELLITES) this.satellites.shift();
    }

    // ======================================================================
    // Satellite merge logic
    // ======================================================================

    _checkSatelliteMerges() {
      const L = this.layout;

      // Group non-merging satellites by (bandIndex, generation)
      const groups = {};
      for (let i = 0; i < this.satellites.length; i++) {
        const sat = this.satellites[i];
        if (sat.merging || sat.generation >= MAX_GENERATION) continue;
        const key = sat.bandIndex + ':' + sat.generation;
        if (!groups[key]) groups[key] = [];
        groups[key].push(i);
      }

      // For each group with >= MERGE_THRESHOLD, initiate merge
      for (const key in groups) {
        const indices = groups[key];
        if (indices.length < MERGE_THRESHOLD) continue;

        // Take the first 5
        const mergeIndices = indices.slice(0, MERGE_THRESHOLD);

        // Compute average position as merge target
        let avgX = 0, avgY = 0;
        for (const idx of mergeIndices) {
          const sat = this.satellites[idx];
          const sx = L.fortressX + Math.cos(sat.orbitAngle) * sat.orbitRadius;
          const sy = L.fortressY + Math.sin(sat.orbitAngle) * sat.orbitRadius * 0.45;
          avgX += sx;
          avgY += sy;
        }
        avgX /= MERGE_THRESHOLD;
        avgY /= MERGE_THRESHOLD;

        for (const idx of mergeIndices) {
          const sat = this.satellites[idx];
          sat.merging       = true;
          sat.mergeTarget   = { x: avgX, y: avgY };
          sat.mergeProgress = 0;
          sat._mergeStart   = this.time;
          sat._mergeGen     = sat.generation;
          sat._mergeBand    = sat.bandIndex;
        }
      }
    }

    _updateSatelliteMerges(dt) {
      const L = this.layout;

      // Advance merge progress for all merging satellites
      for (const sat of this.satellites) {
        if (!sat.merging) continue;
        sat.mergeProgress = clamp((this.time - sat._mergeStart) / MERGE_DUR, 0, 1);
      }

      // Collect all completed merge groups (keyed by gen:band)
      const completed = {};
      for (const sat of this.satellites) {
        if (!sat.merging || sat.mergeProgress < 1) continue;
        const key = sat._mergeGen + ':' + sat._mergeBand;
        if (!completed[key]) {
          completed[key] = { gen: sat._mergeGen, band: sat._mergeBand, x: sat.mergeTarget.x, y: sat.mergeTarget.y };
        }
      }

      // Process all completed groups in one pass
      for (const key in completed) {
        const { gen, band: bandIdx, x: cx, y: cy } = completed[key];

        // Remove merged satellites for this group
        this.satellites = this.satellites.filter(
          sat => !(sat.merging && sat.mergeProgress >= 1 &&
                   sat._mergeGen === gen && sat._mergeBand === bandIdx)
        );

        // Add one upgraded satellite
        const newGen = Math.min(gen + 1, MAX_GENERATION);
        const band   = ORBIT_BANDS[bandIdx];
        this.satellites.push({
          orbitRadius:   band.radius * L.earthRadius,
          orbitAngle:    Math.atan2((cy - L.fortressY) / 0.45, cx - L.fortressX),
          orbitSpeed:    band.speed,
          generation:    newGen,
          startTime:     this.time,
          merging:       false,
          mergeTarget:   null,
          mergeProgress: 0,
          bandIndex:     bandIdx,
        });

        // Merge flash effect
        this.effects.push({ type: 'merge', x: cx, y: cy, startTime: this.time });
      }

      if (Object.keys(completed).length > 0) {
        this.stats.plants = this.satellites.length;
      }
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
      const w = this.canvas.width;
      this._canvasWidth = w;

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
            // Stay scanning until classifyPod is called -- no auto-transition
            break;
          }
          case 'flagged': {
            p.progress = clamp(elapsed / (FLAG_SHAKE + FLAG_EXIT), 0, 1);
            if (elapsed < FLAG_SHAKE) {
              // Shake in place
            } else {
              // Fly RIGHT toward inspection queue panel with slight arc
              const exitT = (elapsed - FLAG_SHAKE) / FLAG_EXIT;
              p.x += dt * (400 + exitT * 300);
              p.y -= dt * (40 - exitT * 80); // slight arc: up then down
            }
            if (p.x > w + p.size * 2) p.state = 'done';
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
              // Convert to orbiting satellite
              this.addSatellite();
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

      // --- Satellites: advance orbit angles + merge logic ---
      for (const sat of this.satellites) {
        if (!sat.merging) {
          sat.orbitAngle += sat.orbitSpeed * dt;
        }
      }
      this._checkSatelliteMerges();
      this._updateSatelliteMerges(dt);

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

      // 4. Earth (replaces fortress dome)
      if (PS.drawEarth) {
        PS.drawEarth(ctx, L.fortressX, L.fortressY, L.earthRadius, {
          time: this.time,
        });
      } else {
        // Fallback to fortress dome if drawEarth not available yet
        PS.drawFortressDome(ctx, L.fortressX, L.fortressY, L.fortressW, L.fortressH, {
          time: this.time,
        });
      }

      // 4b. Draw orbit band rings (faint ellipses)
      ctx.save();
      ctx.strokeStyle = 'rgba(100, 180, 255, 0.08)';
      ctx.lineWidth   = 1;
      for (const band of ORBIT_BANDS) {
        const rx = band.radius * L.earthRadius;
        const ry = rx * 0.45; // perspective squash
        ctx.beginPath();
        ctx.ellipse(L.fortressX, L.fortressY, rx, ry, 0, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();

      // 5. Orbiting satellites (replaces defense turrets)
      for (const sat of this.satellites) {
        let sx, sy;

        if (sat.merging && sat.mergeTarget) {
          // Interpolate from orbit position to merge target
          const orbitX = L.fortressX + Math.cos(sat.orbitAngle) * sat.orbitRadius;
          const orbitY = L.fortressY + Math.sin(sat.orbitAngle) * sat.orbitRadius * 0.45;
          const t = sat.mergeProgress;
          // Ease-in-out
          const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          sx = orbitX + (sat.mergeTarget.x - orbitX) * eased;
          sy = orbitY + (sat.mergeTarget.y - orbitY) * eased;
        } else {
          sx = L.fortressX + Math.cos(sat.orbitAngle) * sat.orbitRadius;
          sy = L.fortressY + Math.sin(sat.orbitAngle) * sat.orbitRadius * 0.45;
        }

        const satSize = clamp(1 + sat.generation * 0.4, 1, 3);

        if (PS.drawSatellite) {
          PS.drawSatellite(ctx, sx, sy, satSize, sat.generation, {
            time: this.time,
          });
        } else {
          // Fallback: draw a simple circle if drawSatellite not available yet
          const r = 3 + sat.generation * 2;
          const genColors = ['#80f0ff', '#4ade80', '#facc15', '#f97316', '#ef4444'];
          ctx.fillStyle = genColors[sat.generation] || '#80f0ff';
          ctx.beginPath();
          ctx.arc(sx, sy, r * satSize * 0.5, 0, Math.PI * 2);
          ctx.fill();
        }
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

      // 8. Landing burst / sparkle / merge flash effects
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
        } else if (ef.type === 'merge') {
          // Merge flash: bright pulse with gold/cyan sparkles
          PS.drawBrainPulse(ctx, ef.x, ef.y, progress, {
            maxRadius: 40,
          });
          for (let i = 0; i < 6; i++) {
            const angle = (i / 6) * Math.PI * 2 + this.time * 3;
            const dist  = progress * 30;
            PS.drawSparkle(
              ctx,
              ef.x + Math.cos(angle) * dist,
              ef.y + Math.sin(angle) * dist,
              8, progress, '#facc15'
            );
          }
        }
      }

      // 9. Scanlines overlay (CRT feel)
      PS.drawScanlines(ctx, w, h, { alpha: 0.03 });
    }
  }

  // Backward compatibility: expose plants getter that returns satellites
  Object.defineProperty(OrbitalEngine.prototype, 'plants', {
    get() { return this.satellites; },
    set(val) { this.satellites = val; },
  });

  return OrbitalEngine;
})();

// Export for both browser (global) and Node/bundler (CommonJS)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OrbitalEngine;
}
