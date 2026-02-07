// ============================================================================
// PixelSprites.js -- Orbital Fortress Pixel Art Sprite System
// ============================================================================
// All visual assets for the Orbital Fortress fraud detection canvas.
// Drawn programmatically with Canvas 2D -- zero external images.
//
// Aesthetic: Sci-fi fortress meets Hyper Light Drifter glow.
// Palette:   Steel & energy-cyan (see PALETTE below).
//
// Every public function signature:
//   drawXxx(ctx, x, y, size, options)
//   - ctx     : CanvasRenderingContext2D
//   - x, y    : center of the sprite
//   - size    : base pixel-unit multiplier (1 = native 16x16 grid)
//   - options : object with optional overrides (time, shake, color, etc.)
// ============================================================================

const PixelSprites = (() => {

  // --------------------------------------------------------------------------
  // PALETTE
  // --------------------------------------------------------------------------
  const C = Object.freeze({
    deepSpace:      '#0a0b14',
    panelDark:      '#1e293b',
    spaceBlue:      '#2b2b3d',
    podBlue:        '#7ec4cf',
    podBlueShadow:  '#5b9aa8',
    podBlueDark:    '#4a8899',
    clearGreen:     '#4ade80',
    clearGreenShadow:'#22c55e',
    steelGray:      '#8a9bb5',
    steelLight:     '#a8b8cc',
    steelDark:      '#5a6d82',
    threatRed:      '#ef4444',
    threatRedShadow:'#b91c1c',
    threatRedDark:  '#991b1b',
    amber:          '#ffb94f',
    darkAmber:      '#c98a2e',
    amberLight:     '#ffd080',
    platformDark:   '#3a4a5e',
    platformDeep:   '#2d3748',
    platformMid:    '#4a5568',
    energyCyan:     '#00e5ff',
    energyBlue:     '#1e88e5',
    energyBright:   '#80f0ff',
    energyPulse:    '#40c4ff',
    white:          '#f5f0e1',
    whiteDim:       '#c0b8a4',
    platformMetal:  '#6b7b8d',
    platformShadow: '#4a5568',
    platformRim:    '#7f8ea0',
    // Backward-compat aliases for untouched sections (pattern icons)
    petalPurple:    '#1e88e5',  // -> energyBlue
  });

  // --------------------------------------------------------------------------
  // HELPERS
  // --------------------------------------------------------------------------

  /** Draw one "pixel" (a scaled rectangle). */
  function px(ctx, baseX, baseY, col, row, s, color) {
    ctx.fillStyle = color;
    ctx.fillRect(
      Math.round(baseX + col * s),
      Math.round(baseY + row * s),
      Math.ceil(s),
      Math.ceil(s)
    );
  }

  /** Draw many pixels from a flat array of [col, row] pairs. */
  function pxBatch(ctx, baseX, baseY, s, color, coords) {
    ctx.fillStyle = color;
    for (let i = 0; i < coords.length; i++) {
      const c = coords[i][0];
      const r = coords[i][1];
      ctx.fillRect(
        Math.round(baseX + c * s),
        Math.round(baseY + r * s),
        Math.ceil(s),
        Math.ceil(s)
      );
    }
  }

  /** Convert hex (#rrggbb) to "rgba(r,g,b,a)". */
  function rgba(hex, alpha) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
  }

  /** Soft radial glow. */
  function glow(ctx, x, y, radius, hex, alpha) {
    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
    grad.addColorStop(0, rgba(hex, alpha));
    grad.addColorStop(0.6, rgba(hex, alpha * 0.4));
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  /** Seeded pseudo-random (deterministic per index). */
  function seededRand(seed) {
    let s = seed;
    return function () {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
  }

  /** Lerp color channels. t in [0,1]. */
  function lerpColor(hexA, hexB, t) {
    const a = parseInt(hexA.slice(1), 16);
    const b = parseInt(hexB.slice(1), 16);
    const r = Math.round(((a >> 16) & 255) * (1 - t) + ((b >> 16) & 255) * t);
    const g = Math.round(((a >> 8) & 255) * (1 - t) + ((b >> 8) & 255) * t);
    const bl = Math.round((a & 255) * (1 - t) + (b & 255) * t);
    return `rgb(${r},${g},${bl})`;
  }


  // ==========================================================================
  // 1.  CARGO POD  (Neutral / Blue)
  // ==========================================================================
  //
  //  16x16 grid.  Small shipping-crate shape with rounded-ish corners,
  //  cross-bracing detail, highlight on top-left, shadow on bottom-right.
  //
  function drawCargoPodNeutral(ctx, x, y, size, options) {
    size  = size || 1;
    options = options || {};
    const s = size;                       // one pixel-unit
    const bx = x - 8 * s;                // top-left of 16x16 grid
    const by = y - 8 * s;
    const showGlow = options.glow !== false;
    const ox = options.offsetX || 0;
    const oy = options.offsetY || 0;
    const X = bx + ox;
    const Y = by + oy;

    // --- glow ---
    if (showGlow) {
      glow(ctx, x + ox, y + oy, 14 * s, C.podBlue, 0.25);
    }

    // --- shadow (bottom-right offset) ---
    pxBatch(ctx, X, Y, s, C.podBlueDark, [
      [4,13],[5,13],[6,13],[7,13],[8,13],[9,13],[10,13],[11,13],
      [12,5],[12,6],[12,7],[12,8],[12,9],[12,10],[12,11],[12,12],
      [13,5],[13,6],[13,7],[13,8],[13,9],[13,10],[13,11],[13,12],[13,13],
    ]);

    // --- main body ---
    pxBatch(ctx, X, Y, s, C.podBlue, [
      // top row (slightly inset for rounded look)
               [5,3],[6,3],[7,3],[8,3],[9,3],[10,3],
      [4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],
      [3,5],[4,5],[5,5],[6,5],[7,5],[8,5],[9,5],[10,5],[11,5],
      [3,6],[4,6],[5,6],[6,6],[7,6],[8,6],[9,6],[10,6],[11,6],
      [3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7],[10,7],[11,7],
      [3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],
      [3,9],[4,9],[5,9],[6,9],[7,9],[8,9],[9,9],[10,9],[11,9],
      [3,10],[4,10],[5,10],[6,10],[7,10],[8,10],[9,10],[10,10],[11,10],
      [3,11],[4,11],[5,11],[6,11],[7,11],[8,11],[9,11],[10,11],[11,11],
      [4,12],[5,12],[6,12],[7,12],[8,12],[9,12],[10,12],[11,12],
    ]);

    // --- cross-bracing (darker bands) ---
    pxBatch(ctx, X, Y, s, C.podBlueShadow, [
      // horizontal band
      [3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],
      // vertical band
      [7,3],[7,4],[7,5],[7,6],[7,7],[7,8],[7,9],[7,10],[7,11],[7,12],
    ]);

    // --- highlight (top-left bevel) ---
    pxBatch(ctx, X, Y, s, rgba(C.white, 0.35), [
      [5,4],[6,4],[7,4],[8,4],
      [4,5],[5,5],
      [4,6],
    ]);

    // --- corner rivets ---
    pxBatch(ctx, X, Y, s, C.podBlueDark, [
      [5,5],[10,5],[5,11],[10,11],
    ]);
  }


  // ==========================================================================
  // 2.  CARGO POD  (Flagged / Red)
  // ==========================================================================
  function drawCargoPodFlagged(ctx, x, y, size, options) {
    size  = size || 1;
    options = options || {};
    const s = size;
    const t = options.time || 0;
    const shakeAmp = options.shake || 0;

    // animated jitter
    const ox = shakeAmp * Math.sin(t * 18) * s;
    const oy = shakeAmp * Math.cos(t * 22) * 0.6 * s;

    const bx = x - 8 * s + ox;
    const by = y - 8 * s + oy;

    // --- pulsing red glow ---
    const glowA = 0.35 + Math.sin(t * 4) * 0.15;
    glow(ctx, x + ox, y + oy, 16 * s, C.threatRed, glowA);

    // --- shadow ---
    pxBatch(ctx, bx, by, s, C.threatRedDark, [
      [4,13],[5,13],[6,13],[7,13],[8,13],[9,13],[10,13],[11,13],
      [12,5],[12,6],[12,7],[12,8],[12,9],[12,10],[12,11],[12,12],
      [13,5],[13,6],[13,7],[13,8],[13,9],[13,10],[13,11],[13,12],[13,13],
    ]);

    // --- body (same shape as neutral, red palette) ---
    pxBatch(ctx, bx, by, s, C.threatRed, [
               [5,3],[6,3],[7,3],[8,3],[9,3],[10,3],
      [4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],
      [3,5],[4,5],[5,5],[6,5],[7,5],[8,5],[9,5],[10,5],[11,5],
      [3,6],[4,6],[5,6],[6,6],[7,6],[8,6],[9,6],[10,6],[11,6],
      [3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7],[10,7],[11,7],
      [3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],
      [3,9],[4,9],[5,9],[6,9],[7,9],[8,9],[9,9],[10,9],[11,9],
      [3,10],[4,10],[5,10],[6,10],[7,10],[8,10],[9,10],[10,10],[11,10],
      [3,11],[4,11],[5,11],[6,11],[7,11],[8,11],[9,11],[10,11],[11,11],
      [4,12],[5,12],[6,12],[7,12],[8,12],[9,12],[10,12],[11,12],
    ]);

    // --- cross-bracing ---
    pxBatch(ctx, bx, by, s, C.threatRedShadow, [
      [3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],
      [7,3],[7,4],[7,5],[7,6],[7,7],[7,8],[7,9],[7,10],[7,11],[7,12],
    ]);

    // --- WARNING TRIANGLE on top ---
    pxBatch(ctx, bx, by, s, C.amber, [
                     [7,0],[8,0],
                [6,1],[7,1],[8,1],[9,1],
           [5,2],[6,2],[7,2],[8,2],[9,2],[10,2],
    ]);
    // exclamation mark inside triangle
    pxBatch(ctx, bx, by, s, C.deepSpace, [
      [7,0],[8,0],   // dot
      [7,1],[8,1],   // line (shares row with triangle interior)
    ]);
    // re-draw the exclamation as dark center
    pxBatch(ctx, bx, by, s, C.threatRedDark, [
      [7,1],[8,1],
    ]);
    // exclamation dot at bottom of triangle
    pxBatch(ctx, bx, by, s, C.deepSpace, [
      [7,2],[8,2],
    ]);
  }


  // ==========================================================================
  // 3.  CARGO POD  (Clear / Green)
  // ==========================================================================
  function drawCargoPodClear(ctx, x, y, size, options) {
    size  = size || 1;
    options = options || {};
    const s = size;
    const showGlow = options.glow !== false;

    const bx = x - 8 * s;
    const by = y - 8 * s;

    if (showGlow) {
      glow(ctx, x, y, 14 * s, C.clearGreen, 0.3);
    }

    // --- shadow ---
    pxBatch(ctx, bx, by, s, '#1a7a3a', [
      [4,13],[5,13],[6,13],[7,13],[8,13],[9,13],[10,13],[11,13],
      [12,5],[12,6],[12,7],[12,8],[12,9],[12,10],[12,11],[12,12],
      [13,5],[13,6],[13,7],[13,8],[13,9],[13,10],[13,11],[13,12],[13,13],
    ]);

    // --- body ---
    pxBatch(ctx, bx, by, s, C.clearGreen, [
               [5,3],[6,3],[7,3],[8,3],[9,3],[10,3],
      [4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],
      [3,5],[4,5],[5,5],[6,5],[7,5],[8,5],[9,5],[10,5],[11,5],
      [3,6],[4,6],[5,6],[6,6],[7,6],[8,6],[9,6],[10,6],[11,6],
      [3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7],[10,7],[11,7],
      [3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],
      [3,9],[4,9],[5,9],[6,9],[7,9],[8,9],[9,9],[10,9],[11,9],
      [3,10],[4,10],[5,10],[6,10],[7,10],[8,10],[9,10],[10,10],[11,10],
      [3,11],[4,11],[5,11],[6,11],[7,11],[8,11],[9,11],[10,11],[11,11],
      [4,12],[5,12],[6,12],[7,12],[8,12],[9,12],[10,12],[11,12],
    ]);

    // --- bracing ---
    pxBatch(ctx, bx, by, s, C.clearGreenShadow, [
      [3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],
      [7,3],[7,4],[7,5],[7,6],[7,7],[7,8],[7,9],[7,10],[7,11],[7,12],
    ]);

    // --- highlight ---
    pxBatch(ctx, bx, by, s, rgba(C.white, 0.3), [
      [5,4],[6,4],[7,4],[8,4],
      [4,5],[5,5],
      [4,6],
    ]);

    // --- CHECKMARK overlay ---
    pxBatch(ctx, bx, by, s, C.white, [
      // left stroke (ascending)
      [4,8],[5,9],
      [5,8],[6,9],
      // bottom vertex
      [6,10],[7,10],
      // right stroke (ascending)
      [7,9],[8,8],[9,7],[10,6],
      [8,9],[9,8],[10,7],[11,6],
    ]);
  }


  // ==========================================================================
  // 4a. DEATH STAR (center icon for defense grid)
  // ==========================================================================
  //
  //  Canvas arc/path Death Star.  Larger than 16x16, so we use arc() ops
  //  rather than the pixel grid.
  //
  //  Parameters:
  //    ctx     - CanvasRenderingContext2D
  //    x, y    - center
  //    radius  - sphere radius in pixels
  //    options - { time }
  //
  function drawDeathStar(ctx, x, y, radius, options) {
    options = options || {};
    const t = options.time || 0;
    const r = radius;

    ctx.save();

    // --- main body: filled circle ---
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = C.steelGray;
    ctx.fill();

    // --- right-half shadow (clip to right semicircle) ---
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r, -Math.PI * 0.5, Math.PI * 0.5);
    ctx.closePath();
    ctx.clip();
    ctx.fillStyle = rgba(C.steelDark, 0.55);
    ctx.fillRect(x, y - r, r, r * 2);
    ctx.restore();

    // --- surface panel grid lines (subtle) ---
    ctx.strokeStyle = rgba('#000000', 0.08);
    ctx.lineWidth = 0.8;
    // horizontal lines
    const hLines = 5;
    for (let i = 1; i < hLines; i++) {
      const ly = y - r + (2 * r * i) / hLines;
      const dx = Math.sqrt(r * r - (ly - y) * (ly - y));
      ctx.beginPath();
      ctx.moveTo(x - dx, ly);
      ctx.lineTo(x + dx, ly);
      ctx.stroke();
    }
    // vertical lines
    const vLines = 5;
    for (let i = 1; i < vLines; i++) {
      const lx = x - r + (2 * r * i) / vLines;
      const dy = Math.sqrt(r * r - (lx - x) * (lx - x));
      ctx.beginPath();
      ctx.moveTo(lx, y - dy);
      ctx.lineTo(lx, y + dy);
      ctx.stroke();
    }

    // --- equatorial trench (horizontal band across center) ---
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = rgba(C.platformDeep, 0.45);
    ctx.fillRect(x - r, y - r * 0.04, r * 2, r * 0.08);
    // trench detail lines
    ctx.strokeStyle = rgba('#000000', 0.2);
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(x - r, y - r * 0.04);
    ctx.lineTo(x + r, y - r * 0.04);
    ctx.moveTo(x - r, y + r * 0.04);
    ctx.lineTo(x + r, y + r * 0.04);
    ctx.stroke();
    ctx.restore();

    // --- superlaser dish (concave hemisphere, upper-right quadrant) ---
    const dishCx = x + r * 0.3;
    const dishCy = y - r * 0.25;
    const dishR = r * 0.28;

    ctx.save();
    // clip to main sphere
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.clip();

    // dish concavity (dark circle)
    ctx.beginPath();
    ctx.arc(dishCx, dishCy, dishR, 0, Math.PI * 2);
    ctx.fillStyle = C.platformDeep;
    ctx.fill();

    // dish inner ring
    ctx.beginPath();
    ctx.arc(dishCx, dishCy, dishR * 0.7, 0, Math.PI * 2);
    ctx.fillStyle = rgba('#1a2030', 0.8);
    ctx.fill();

    // dish rim highlight
    ctx.beginPath();
    ctx.arc(dishCx, dishCy, dishR, 0, Math.PI * 2);
    ctx.strokeStyle = rgba(C.steelLight, 0.4);
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.restore();

    // --- superlaser energy point (pulsing glow) ---
    const pulseA = 0.5 + Math.sin(t * 3) * 0.25;
    glow(ctx, dishCx, dishCy, dishR * 1.2, C.energyCyan, pulseA * 0.4);
    glow(ctx, dishCx, dishCy, dishR * 0.5, C.energyCyan, pulseA * 0.7);
    // bright core dot
    ctx.beginPath();
    ctx.arc(dishCx, dishCy, r * 0.03, 0, Math.PI * 2);
    ctx.fillStyle = rgba(C.energyBright, pulseA);
    ctx.fill();

    // --- sphere outline ---
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.strokeStyle = rgba('#000000', 0.3);
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // --- top-left specular highlight ---
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.clip();
    const specGrad = ctx.createRadialGradient(
      x - r * 0.35, y - r * 0.35, 0,
      x - r * 0.35, y - r * 0.35, r * 0.6
    );
    specGrad.addColorStop(0, rgba(C.white, 0.15));
    specGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = specGrad;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
    ctx.restore();

    ctx.restore();
  }


  // ==========================================================================
  // 4b. EARTH (full spherical planet)
  // ==========================================================================
  //
  //  Canvas arc/path Earth.  Ocean, continents, ice caps, clouds, atmosphere.
  //
  //  Parameters:
  //    ctx     - CanvasRenderingContext2D
  //    x, y    - center
  //    radius  - sphere radius in pixels
  //    options - { time }
  //
  function drawEarth(ctx, x, y, radius, options) {
    options = options || {};
    const t = options.time || 0;
    const r = radius;

    ctx.save();

    // --- base ocean sphere ---
    const oceanGrad = ctx.createRadialGradient(
      x - r * 0.3, y - r * 0.3, 0,
      x, y, r
    );
    oceanGrad.addColorStop(0, '#1976d2');
    oceanGrad.addColorStop(0.7, '#1565c0');
    oceanGrad.addColorStop(1, '#0d47a1');
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = oceanGrad;
    ctx.fill();

    // clip all surface features to the sphere
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.clip();

    // --- continents (simplified blobs) ---
    // slow "rotation" offset
    const rotOffset = Math.sin(t * 0.05) * r * 0.1;

    // continent 1 (Americas-like, left-center)
    ctx.fillStyle = '#2e7d32';
    ctx.beginPath();
    ctx.ellipse(x - r * 0.2 + rotOffset, y - r * 0.15, r * 0.2, r * 0.35, -0.3, 0, Math.PI * 2);
    ctx.fill();
    // sub-blob (South America)
    ctx.beginPath();
    ctx.ellipse(x - r * 0.15 + rotOffset, y + r * 0.25, r * 0.12, r * 0.2, 0.2, 0, Math.PI * 2);
    ctx.fill();

    // continent 2 (Eurasia-like, upper right)
    ctx.fillStyle = '#33691e';
    ctx.beginPath();
    ctx.ellipse(x + r * 0.3 + rotOffset, y - r * 0.2, r * 0.3, r * 0.15, 0.1, 0, Math.PI * 2);
    ctx.fill();

    // continent 3 (Africa-like, center right)
    ctx.fillStyle = '#8d6e63';
    ctx.beginPath();
    ctx.ellipse(x + r * 0.15 + rotOffset, y + r * 0.1, r * 0.12, r * 0.22, 0.15, 0, Math.PI * 2);
    ctx.fill();

    // continent 4 (small island, lower left)
    ctx.fillStyle = '#2e7d32';
    ctx.beginPath();
    ctx.ellipse(x - r * 0.4 + rotOffset, y + r * 0.35, r * 0.08, r * 0.06, 0, 0, Math.PI * 2);
    ctx.fill();

    // --- ice caps ---
    ctx.fillStyle = rgba('#e0e0e0', 0.7);
    // north pole
    ctx.beginPath();
    ctx.ellipse(x, y - r * 0.88, r * 0.35, r * 0.1, 0, 0, Math.PI * 2);
    ctx.fill();
    // south pole
    ctx.beginPath();
    ctx.ellipse(x, y + r * 0.9, r * 0.3, r * 0.08, 0, 0, Math.PI * 2);
    ctx.fill();

    // --- cloud wisps (semi-transparent, drifting) ---
    ctx.fillStyle = rgba('#ffffff', 0.18);
    const cloudDrift = t * 0.08;
    // cloud 1
    ctx.beginPath();
    ctx.ellipse(x - r * 0.3 + Math.sin(cloudDrift) * r * 0.15, y - r * 0.4, r * 0.25, r * 0.05, 0.3, 0, Math.PI * 2);
    ctx.fill();
    // cloud 2
    ctx.beginPath();
    ctx.ellipse(x + r * 0.2 + Math.sin(cloudDrift + 1.5) * r * 0.1, y + r * 0.05, r * 0.2, r * 0.04, -0.2, 0, Math.PI * 2);
    ctx.fill();
    // cloud 3
    ctx.beginPath();
    ctx.ellipse(x + Math.sin(cloudDrift + 3) * r * 0.12, y + r * 0.35, r * 0.18, r * 0.04, 0.1, 0, Math.PI * 2);
    ctx.fill();

    // --- space shadow (darken right ~30%) ---
    const shadowGrad = ctx.createLinearGradient(x + r * 0.3, y, x + r, y);
    shadowGrad.addColorStop(0, 'rgba(0,0,0,0)');
    shadowGrad.addColorStop(1, 'rgba(0,0,0,0.45)');
    ctx.fillStyle = shadowGrad;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);

    ctx.restore(); // end clip

    // --- atmosphere glow ring ---
    ctx.beginPath();
    ctx.arc(x, y, r + 2, 0, Math.PI * 2);
    ctx.strokeStyle = rgba('#64b5f6', 0.2);
    ctx.lineWidth = 4;
    ctx.stroke();

    glow(ctx, x, y, r + 8, '#64b5f6', 0.08);

    // --- sphere outline ---
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.strokeStyle = rgba('#0d47a1', 0.4);
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.restore();
  }


  // ==========================================================================
  // 4c. SATELLITE (5 generations, pixel art style)
  // ==========================================================================
  //
  //  Parameters:
  //    ctx        - CanvasRenderingContext2D
  //    x, y       - center of the sprite
  //    size       - base pixel unit multiplier
  //    generation - 0..4
  //    options    - { time }
  //
  function drawSatellite(ctx, x, y, size, generation, options) {
    size = size || 1;
    generation = generation || 0;
    options = options || {};
    const s = size;
    const t = options.time || 0;
    const gen = Math.max(0, Math.min(4, Math.floor(generation)));

    switch (gen) {

      // -- Gen 0: tiny 8x8 satellite --
      case 0: {
        const bx = x - 4 * s;
        const by = y - 4 * s;

        glow(ctx, x, y, 6 * s, C.energyCyan, 0.15);

        // body (3x2)
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [3,3],[4,3],[5,3],
          [3,4],[4,4],[5,4],
        ]);
        // left solar panel (2x1)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [1,3],[2,3],
        ]);
        // right solar panel (2x1)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [6,3],[7,3],
        ]);
        // panel connector
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [2,4],[6,4],
        ]);
        // antenna
        pxBatch(ctx, bx, by, s, C.steelLight, [
          [4,2],[4,1],
        ]);
        // blinking light at top
        const blink0 = Math.sin(t * 5) > 0.3 ? 0.9 : 0.1;
        pxBatch(ctx, bx, by, s, rgba(C.white, blink0), [
          [4,1],
        ]);
        // panel shimmer
        const shimmer0 = 0.3 + Math.sin(t * 2) * 0.15;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, shimmer0), [
          [1,3],[7,3],
        ]);
        break;
      }

      // -- Gen 1: small 10x10 satellite --
      case 1: {
        const bx = x - 5 * s;
        const by = y - 5 * s;

        glow(ctx, x, y, 8 * s, C.energyCyan, 0.18);

        // body (4x3)
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [3,4],[4,4],[5,4],[6,4],
          [3,5],[4,5],[5,5],[6,5],
          [3,6],[4,6],[5,6],[6,6],
        ]);
        // body highlight
        pxBatch(ctx, bx, by, s, C.steelLight, [
          [3,4],[4,4],
        ]);
        // left solar panels (3x2)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [0,4],[1,4],[2,4],
          [0,5],[1,5],[2,5],
        ]);
        // right solar panels (3x2)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [7,4],[8,4],[9,4],
          [7,5],[8,5],[9,5],
        ]);
        // antenna dish
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [4,3],[5,3],
          [4,2],[5,2],[6,2],
        ]);
        // antenna tip
        pxBatch(ctx, bx, by, s, C.amber, [
          [5,1],
        ]);
        // blinking light
        const blink1 = Math.sin(t * 4) > 0.2 ? 0.85 : 0.1;
        pxBatch(ctx, bx, by, s, rgba(C.white, blink1), [
          [5,1],
        ]);
        // panel shimmer
        const shimmer1 = 0.25 + Math.sin(t * 2.5) * 0.2;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, shimmer1), [
          [0,4],[9,4],
        ]);
        break;
      }

      // -- Gen 2: medium 14x14 satellite --
      case 2: {
        const bx = x - 7 * s;
        const by = y - 7 * s;

        glow(ctx, x, y, 10 * s, C.energyCyan, 0.2);

        // cylindrical body (5x4)
        pxBatch(ctx, bx, by, s, C.steelLight, [
          [5,5],[6,5],[7,5],[8,5],[9,5],
          [5,6],[6,6],[7,6],[8,6],[9,6],
          [5,7],[6,7],[7,7],[8,7],[9,7],
          [5,8],[6,8],[7,8],[8,8],[9,8],
        ]);
        // body shadow (right side)
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [9,5],[9,6],[9,7],[9,8],
          [8,8],[9,8],
        ]);
        // left solar panels (4x3, double array)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [0,5],[1,5],[2,5],[3,5],
          [0,6],[1,6],[2,6],[3,6],
          [0,7],[1,7],[2,7],[3,7],
        ]);
        // panel divider
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [4,5],[4,6],[4,7],
        ]);
        // right solar panels (4x3, double array)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [10,5],[11,5],[12,5],[13,5],
          [10,6],[11,6],[12,6],[13,6],
          [10,7],[11,7],[12,7],[13,7],
        ]);
        // panel divider
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [10,5],[10,6],[10,7],
        ]);
        // dish antenna pointing up
        pxBatch(ctx, bx, by, s, C.energyBlue, [
          [6,4],[7,4],[8,4],
          [5,3],[6,3],[7,3],[8,3],[9,3],
          [6,2],[7,2],[8,2],
        ]);
        // dish stem
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [7,4],[7,5],
        ]);
        // blinking lights
        const blink2a = Math.sin(t * 3.5) > 0.3 ? 0.8 : 0.1;
        const blink2b = Math.sin(t * 3.5 + Math.PI) > 0.3 ? 0.8 : 0.1;
        pxBatch(ctx, bx, by, s, rgba(C.energyCyan, blink2a), [
          [5,5],
        ]);
        pxBatch(ctx, bx, by, s, rgba(C.threatRed, blink2b), [
          [9,5],
        ]);
        // solar panel shimmer
        const shimmer2 = 0.2 + Math.sin(t * 2) * 0.15;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, shimmer2), [
          [0,5],[1,6],[13,5],[12,6],
        ]);
        break;
      }

      // -- Gen 3: large 18x18 modular station --
      case 3: {
        const bx = x - 9 * s;
        const by = y - 9 * s;

        glow(ctx, x, y, 14 * s, C.energyCyan, 0.22);

        // modular body (7x5)
        pxBatch(ctx, bx, by, s, C.steelLight, [
          [6,7],[7,7],[8,7],[9,7],[10,7],[11,7],[12,7],
          [6,8],[7,8],[8,8],[9,8],[10,8],[11,8],[12,8],
          [6,9],[7,9],[8,9],[9,9],[10,9],[11,9],[12,9],
          [6,10],[7,10],[8,10],[9,10],[10,10],[11,10],[12,10],
          [6,11],[7,11],[8,11],[9,11],[10,11],[11,11],[12,11],
        ]);
        // body panel lines
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [9,7],[9,8],[9,9],[9,10],[9,11],
          [6,9],[7,9],[8,9],[9,9],[10,9],[11,9],[12,9],
        ]);
        // body shadow
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [12,7],[12,8],[12,9],[12,10],[12,11],
          [11,11],[12,11],
        ]);
        // left solar arrays (multi-segment)
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [0,7],[1,7],[2,7],[3,7],[4,7],
          [0,8],[1,8],[2,8],[3,8],[4,8],
          [0,9],[1,9],[2,9],[3,9],[4,9],
          [0,10],[1,10],[2,10],[3,10],[4,10],
          [0,11],[1,11],[2,11],[3,11],[4,11],
        ]);
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [5,7],[5,8],[5,9],[5,10],[5,11],
          [2,7],[2,8],[2,9],[2,10],[2,11],
        ]);
        // right solar arrays
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [13,7],[14,7],[15,7],[16,7],[17,7],
          [13,8],[14,8],[15,8],[16,8],[17,8],
          [13,9],[14,9],[15,9],[16,9],[17,9],
          [13,10],[14,10],[15,10],[16,10],[17,10],
          [13,11],[14,11],[15,11],[16,11],[17,11],
        ]);
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [13,7],[13,8],[13,9],[13,10],[13,11],
          [15,7],[15,8],[15,9],[15,10],[15,11],
        ]);
        // dish antenna 1 (upper left)
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [7,6],[8,6],
          [6,5],[7,5],[8,5],[9,5],
          [7,4],[8,4],
        ]);
        pxBatch(ctx, bx, by, s, C.steelLight, [
          [7,4],
        ]);
        // dish antenna 2 (upper right)
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [10,6],[11,6],
          [10,5],[11,5],[12,5],
          [11,4],
        ]);
        // docking port (bottom center)
        pxBatch(ctx, bx, by, s, C.platformDeep, [
          [8,12],[9,12],[10,12],
          [9,13],
        ]);
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [8,12],[10,12],
        ]);
        // energy glows
        const glow3a = 0.4 + Math.sin(t * 3) * 0.2;
        glow(ctx, bx + 7.5 * s, by + 4 * s, 3 * s, C.energyBright, glow3a);
        glow(ctx, bx + 11 * s, by + 4 * s, 2.5 * s, C.energyBright, glow3a * 0.7);
        // blinking lights
        const blink3 = Math.sin(t * 4) > 0.2 ? 0.9 : 0.15;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, blink3), [
          [6,7],[12,7],
        ]);
        const blink3b = Math.sin(t * 4 + 2) > 0.2 ? 0.8 : 0.1;
        pxBatch(ctx, bx, by, s, rgba(C.threatRed, blink3b), [
          [9,12],
        ]);
        // solar panel shimmer
        const shimmer3 = 0.2 + Math.sin(t * 1.8) * 0.15;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, shimmer3), [
          [0,8],[1,9],[4,7],[17,8],[16,9],[14,7],
        ]);
        break;
      }

      // -- Gen 4: mega 22x22 ring station --
      case 4: {
        const bx = x - 11 * s;
        const by = y - 11 * s;

        // outer energy field glow
        const fieldA = 0.12 + Math.sin(t * 1.5) * 0.06;
        glow(ctx, x, y, 16 * s, C.energyCyan, fieldA);

        // ring structure (outer)
        const ringCoords = [];
        // top arc
        for (let i = 5; i <= 16; i++) { ringCoords.push([i, 2]); ringCoords.push([i, 3]); }
        // bottom arc
        for (let i = 5; i <= 16; i++) { ringCoords.push([i, 18]); ringCoords.push([i, 19]); }
        // left arc
        for (let i = 5; i <= 16; i++) { ringCoords.push([2, i]); ringCoords.push([3, i]); }
        // right arc
        for (let i = 5; i <= 16; i++) { ringCoords.push([18, i]); ringCoords.push([19, i]); }
        // corners
        ringCoords.push([4, 3], [3, 4], [4, 4]);
        ringCoords.push([17, 3], [18, 4], [17, 4]);
        ringCoords.push([3, 17], [4, 18], [4, 17]);
        ringCoords.push([18, 17], [17, 18], [17, 17]);

        pxBatch(ctx, bx, by, s, C.steelLight, ringCoords);

        // ring shadow (right and bottom edges)
        const ringShadow = [];
        for (let i = 5; i <= 16; i++) { ringShadow.push([19, i]); ringShadow.push([i, 19]); }
        ringShadow.push([18, 17], [17, 18]);
        pxBatch(ctx, bx, by, s, C.steelDark, ringShadow);

        // ring panel detail lines
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [7, 2], [11, 2], [14, 2],
          [7, 19], [11, 19], [14, 19],
          [2, 7], [2, 11], [2, 14],
          [19, 7], [19, 11], [19, 14],
        ]);

        // central hub (4x4)
        pxBatch(ctx, bx, by, s, C.steelGray, [
          [9, 9], [10, 9], [11, 9], [12, 9],
          [9, 10], [10, 10], [11, 10], [12, 10],
          [9, 11], [10, 11], [11, 11], [12, 11],
          [9, 12], [10, 12], [11, 12], [12, 12],
        ]);
        pxBatch(ctx, bx, by, s, C.steelLight, [
          [9, 9], [10, 9], [9, 10],
        ]);

        // spokes connecting hub to ring
        pxBatch(ctx, bx, by, s, C.steelDark, [
          // top spoke
          [10, 4], [11, 4], [10, 5], [11, 5], [10, 6], [11, 6], [10, 7], [11, 7], [10, 8], [11, 8],
          // bottom spoke
          [10, 13], [11, 13], [10, 14], [11, 14], [10, 15], [11, 15], [10, 16], [11, 16], [10, 17], [11, 17],
          // left spoke
          [4, 10], [4, 11], [5, 10], [5, 11], [6, 10], [6, 11], [7, 10], [7, 11], [8, 10], [8, 11],
          // right spoke
          [13, 10], [13, 11], [14, 10], [14, 11], [15, 10], [15, 11], [16, 10], [16, 11], [17, 10], [17, 11],
        ]);

        // massive solar arrays (extending outside ring)
        // top arrays
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [1, 0], [2, 0], [3, 0], [4, 0],
          [1, 1], [2, 1], [3, 1], [4, 1],
          [17, 0], [18, 0], [19, 0], [20, 0],
          [17, 1], [18, 1], [19, 1], [20, 1],
        ]);
        // bottom arrays
        pxBatch(ctx, bx, by, s, C.energyCyan, [
          [1, 20], [2, 20], [3, 20], [4, 20],
          [1, 21], [2, 21], [3, 21], [4, 21],
          [17, 20], [18, 20], [19, 20], [20, 20],
          [17, 21], [18, 21], [19, 21], [20, 21],
        ]);
        // array connectors
        pxBatch(ctx, bx, by, s, C.steelDark, [
          [4, 2], [17, 2], [4, 19], [17, 19],
        ]);

        // central energy field glow
        const hubGlow = 0.35 + Math.sin(t * 2) * 0.2;
        glow(ctx, x, y, 5 * s, C.energyCyan, hubGlow);

        // particle effects (orbiting the ring)
        const pCount = 8;
        for (let i = 0; i < pCount; i++) {
          const angle = (i / pCount) * Math.PI * 2 + t * 0.5;
          const dist = 9.5 * s;
          const ppx = x + Math.cos(angle) * dist;
          const ppy = y + Math.sin(angle) * dist;
          const pa = 0.3 + Math.sin(t * 3 + i * 1.7) * 0.2;
          ctx.fillStyle = rgba(C.energyBright, pa);
          ctx.fillRect(Math.round(ppx), Math.round(ppy), Math.ceil(s * 0.7), Math.ceil(s * 0.7));
        }

        // blinking lights around ring
        const blink4a = Math.sin(t * 3) > 0.2 ? 0.85 : 0.1;
        const blink4b = Math.sin(t * 3 + Math.PI) > 0.2 ? 0.85 : 0.1;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, blink4a), [
          [5, 2], [16, 2], [2, 5], [19, 16],
        ]);
        pxBatch(ctx, bx, by, s, rgba(C.threatRed, blink4b), [
          [5, 19], [16, 19], [2, 16], [19, 5],
        ]);
        // solar shimmer
        const shimmer4 = 0.25 + Math.sin(t * 2.2) * 0.15;
        pxBatch(ctx, bx, by, s, rgba(C.energyBright, shimmer4), [
          [1, 0], [20, 0], [1, 21], [20, 21],
        ]);
        break;
      }
    }
  }


  // ==========================================================================
  // 4d. DEFENSE GRID RING
  // ==========================================================================
  //
  //  Concentric circles + scanning beam + Death Star at center.
  //  Drawn at (x, y) with given radius as the middle ring.
  //
  function drawDefenseGrid(ctx, x, y, radius, options) {
    options = options || {};
    const scanAngle   = options.scanAngle   || 0;
    const pulsePhase  = options.pulsePhase  || 0;
    const time        = options.time        || 0;

    ctx.save();

    // -- outer ring (dashed, 20% opacity) --
    const outerR = radius * 1.25;
    ctx.strokeStyle = rgba(C.amber, 0.2);
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.arc(x, y, outerR, 0, Math.PI * 2);
    ctx.stroke();

    // -- middle ring (solid, 50% opacity) --
    ctx.setLineDash([]);
    ctx.strokeStyle = rgba(C.amber, 0.45);
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.stroke();

    // -- inner ring (solid, pulsing, with glow) --
    const innerR = radius * 0.72 + Math.sin(pulsePhase) * 2;
    glow(ctx, x, y, innerR + 15, C.amber, 0.18);
    ctx.strokeStyle = rgba(C.amber, 0.75);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(x, y, innerR, 0, Math.PI * 2);
    ctx.stroke();

    // -- tick marks on middle ring --
    const tickCount = 36;
    for (let i = 0; i < tickCount; i++) {
      const a = (i / tickCount) * Math.PI * 2;
      const inner = radius - 4;
      const outer = radius + 4;
      ctx.strokeStyle = rgba(C.amber, 0.25);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + Math.cos(a) * inner, y + Math.sin(a) * inner);
      ctx.lineTo(x + Math.cos(a) * outer, y + Math.sin(a) * outer);
      ctx.stroke();
    }

    // -- scanner beam (sweeping line) --
    const beamLen = outerR;
    const bx = x + Math.cos(scanAngle) * beamLen;
    const by = y + Math.sin(scanAngle) * beamLen;

    // wide glow beam
    const beamGrad = ctx.createLinearGradient(x, y, bx, by);
    beamGrad.addColorStop(0, rgba(C.amber, 0.5));
    beamGrad.addColorStop(1, rgba(C.amber, 0));
    ctx.strokeStyle = beamGrad;
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(bx, by);
    ctx.stroke();

    // crisp center line
    ctx.strokeStyle = rgba(C.amber, 0.7);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(bx, by);
    ctx.stroke();

    // scanner sweep cone (fading triangle)
    const coneSpread = 0.12; // radians
    ctx.fillStyle = rgba(C.amber, 0.06);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.arc(x, y, outerR, scanAngle - coneSpread, scanAngle + coneSpread);
    ctx.closePath();
    ctx.fill();

    ctx.restore();

    // -- Death Star at center (replaces old shield icon) --
    drawDeathStar(ctx, x, y, radius * 0.35, { time });
  }


  // ==========================================================================
  // 5.  DEFENSE TURRET STAGES  (4 frames, each 16x16)
  // ==========================================================================

  // -- Shared: armored metal platform (bottom of each turret sprite) --
  function _drawPlatform(ctx, bx, by, s) {
    // platform rim
    pxBatch(ctx, bx, by, s, C.platformRim, [
      [3,11],[4,11],[5,11],[6,11],[7,11],[8,11],[9,11],[10,11],[11,11],[12,11],
    ]);
    // platform body
    pxBatch(ctx, bx, by, s, C.platformMetal, [
      [4,12],[5,12],[6,12],[7,12],[8,12],[9,12],[10,12],[11,12],
      [4,13],[5,13],[6,13],[7,13],[8,13],[9,13],[10,13],[11,13],
      [5,14],[6,14],[7,14],[8,14],[9,14],[10,14],
    ]);
    // platform shadow (right side)
    pxBatch(ctx, bx, by, s, C.platformShadow, [
      [9,12],[10,12],[11,12],
      [9,13],[10,13],[11,13],
      [9,14],[10,14],
    ]);
    // energy indicator line at row 11
    pxBatch(ctx, bx, by, s, C.energyCyan, [
      [5,11],[6,11],[7,11],[8,11],[9,11],[10,11],
    ]);
    pxBatch(ctx, bx, by, s, rgba(C.energyCyan, 0.4), [
      [6,11],[8,11],
    ]);
  }

  // 5a. TURRET BASE -- unpowered mount on platform
  function drawTurretBase(ctx, x, y, size, options) {
    size = size || 1;
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;

    _drawPlatform(ctx, bx, by, s);

    // small 2x2 steel block (unpowered mount)
    pxBatch(ctx, bx, by, s, C.steelDark, [
      [7,9],[8,9],
      [7,10],[8,10],
    ]);
    pxBatch(ctx, bx, by, s, C.steelGray, [
      [7,9],
    ]);
    // shadow detail
    pxBatch(ctx, bx, by, s, C.platformDark, [
      [8,10],
    ]);
    // dim power dot at row 8 center
    pxBatch(ctx, bx, by, s, rgba(C.energyCyan, 0.3), [
      [7,8],
    ]);
  }

  // 5b. TURRET ACTIVATING -- antenna rising from platform with energy pulse
  function drawTurretActivating(ctx, x, y, size, options) {
    size = size || 1;
    options = options || {};
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;
    const t = options.time || 0;

    _drawPlatform(ctx, bx, by, s);

    // vertical antenna (rows 5-10)
    pxBatch(ctx, bx, by, s, C.steelGray, [
      [7,10],[7,9],[7,8],[7,7],[7,6],[7,5],
    ]);

    // antenna highlight
    pxBatch(ctx, bx, by, s, C.steelLight, [
      [7,5],[7,6],
    ]);

    // dim energy pulse glow at top
    const pulseA = 0.3 + Math.sin(t * 3) * 0.15;
    glow(ctx, bx + 7.5 * s, by + 5 * s, 4 * s, C.energyCyan, pulseA);
    pxBatch(ctx, bx, by, s, rgba(C.energyCyan, pulseA), [
      [7,4],
    ]);
  }

  // 5c. TURRET ONLINE -- active turret with barrel and scanning beam
  function drawTurretOnline(ctx, x, y, size, options) {
    size = size || 1;
    options = options || {};
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;
    const t = options.time || 0;

    _drawPlatform(ctx, bx, by, s);

    // wider base (rows 8-10)
    pxBatch(ctx, bx, by, s, C.steelDark, [
      [6,10],[7,10],[8,10],[9,10],
      [6,9],[7,9],[8,9],[9,9],
      [6,8],[7,8],[8,8],[9,8],
    ]);
    // base highlight
    pxBatch(ctx, bx, by, s, C.steelGray, [
      [6,8],[7,8],[6,9],
    ]);

    // barrel extending up (rows 3-7)
    pxBatch(ctx, bx, by, s, C.steelGray, [
      [7,7],[8,7],
      [7,6],[8,6],
      [7,5],[8,5],
      [7,4],[8,4],
      [7,3],[8,3],
    ]);
    // barrel highlight
    pxBatch(ctx, bx, by, s, C.steelLight, [
      [7,3],[7,4],[7,5],
    ]);

    // scanning beam line from top going right
    const scanLen = 3 + Math.sin(t * 2) * 1;
    for (let i = 0; i < scanLen; i++) {
      const alpha = 0.6 - (i / scanLen) * 0.5;
      pxBatch(ctx, bx, by, s, rgba(C.energyCyan, alpha), [
        [9 + i, 3],
      ]);
    }
    // scan source glow
    glow(ctx, bx + 8.5 * s, by + 3 * s, 3 * s, C.energyCyan, 0.35);
  }

  // 5d. TURRET FULL POWER -- full defense tower with shield projection
  function drawTurretFullPower(ctx, x, y, size, options) {
    size = size || 1;
    options = options || {};
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;
    const shieldColor = options.petalColor || C.energyCyan;
    const t = options.time || 0;

    _drawPlatform(ctx, bx, by, s);

    // thick base (rows 8-10)
    pxBatch(ctx, bx, by, s, C.steelDark, [
      [5,10],[6,10],[7,10],[8,10],[9,10],[10,10],
      [5,9],[6,9],[7,9],[8,9],[9,9],[10,9],
      [6,8],[7,8],[8,8],[9,8],
    ]);
    // base highlights
    pxBatch(ctx, bx, by, s, C.steelGray, [
      [5,9],[6,9],[6,8],[7,8],
    ]);
    // base shadow
    pxBatch(ctx, bx, by, s, C.platformDark, [
      [10,10],[10,9],[9,10],
    ]);

    // barrel (rows 3-7)
    pxBatch(ctx, bx, by, s, C.steelGray, [
      [7,7],[8,7],
      [7,6],[8,6],
      [7,5],[8,5],
      [7,4],[8,4],
      [7,3],[8,3],
    ]);
    // barrel highlight
    pxBatch(ctx, bx, by, s, C.steelLight, [
      [7,3],[7,4],[7,5],[7,6],
    ]);

    // muzzle flash at top
    const flashA = 0.5 + Math.sin(t * 6) * 0.3;
    pxBatch(ctx, bx, by, s, rgba(C.energyCyan, flashA), [
      [7,2],[8,2],
    ]);
    glow(ctx, bx + 7.5 * s, by + 2 * s, 4 * s, C.energyCyan, flashA * 0.6);

    // shield projection arc above (cyan arc)
    ctx.save();
    ctx.strokeStyle = rgba(shieldColor, 0.4 + Math.sin(t * 2) * 0.15);
    ctx.lineWidth = 1.5 * s;
    ctx.beginPath();
    ctx.arc(bx + 7.5 * s, by + 2 * s, 5 * s, Math.PI * 1.1, Math.PI * 1.9);
    ctx.stroke();
    ctx.restore();

    // energy particles floating upward
    const pCount = 6;
    for (let i = 0; i < pCount; i++) {
      const angle = (i / pCount) * Math.PI + Math.PI;
      const dist = 4 * s + Math.sin(t * 3 + i * 1.5) * 2 * s;
      const epx = bx + 7.5 * s + Math.cos(angle) * dist;
      const epy = by + 1 * s + Math.sin(angle) * dist * 0.5 - Math.abs(Math.sin(t * 2 + i)) * 2 * s;
      const pa = 0.3 + Math.sin(t * 4 + i * 2) * 0.2;
      ctx.fillStyle = rgba(shieldColor, pa);
      ctx.fillRect(Math.round(epx), Math.round(epy), Math.ceil(s * 0.8), Math.ceil(s * 0.8));
    }
  }


  // ==========================================================================
  // 6.  FORTRESS DOME (Energy Shield)
  // ==========================================================================
  //
  //  Semi-circular dome with energy shield segments, cyan glow,
  //  shield generator at apex.  Drawn behind the turrets.
  //
  function drawFortressDome(ctx, x, y, width, height, options) {
    options = options || {};
    const time = options.time || 0;
    ctx.save();

    const domeW = width * 0.5;
    const domeH = height * 0.45;
    const baseY = y + height * 0.5;

    // --- cyan interior glow ---
    const interiorGrad = ctx.createRadialGradient(x, baseY - domeH * 0.3, 0, x, baseY - domeH * 0.3, domeW);
    interiorGrad.addColorStop(0, rgba(C.energyCyan, 0.12));
    interiorGrad.addColorStop(0.5, rgba(C.energyCyan, 0.04));
    interiorGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = interiorGrad;
    ctx.beginPath();
    ctx.ellipse(x, baseY, domeW, domeH, 0, Math.PI, 0, true);
    ctx.fill();

    // --- dome outline (energy shield) ---
    ctx.strokeStyle = rgba(C.energyCyan, 0.5);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(x, baseY, domeW, domeH, 0, Math.PI, 0, true);
    ctx.stroke();

    // --- base platform line ---
    ctx.strokeStyle = rgba(C.energyCyan, 0.3);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x - domeW - 10, baseY);
    ctx.lineTo(x + domeW + 10, baseY);
    ctx.stroke();

    // --- energy shield segments (vertical ribs) ---
    ctx.strokeStyle = rgba(C.energyCyan, 0.15);
    ctx.lineWidth = 1;
    const ribCount = 7;
    for (let i = 0; i < ribCount; i++) {
      const t = (i + 1) / (ribCount + 1);
      const ribX = x - domeW + t * domeW * 2;
      const relX = (ribX - x) / domeW;
      const ribTop = baseY - domeH * Math.sqrt(1 - relX * relX);
      ctx.beginPath();
      ctx.moveTo(ribX, baseY);
      ctx.lineTo(ribX, ribTop);
      ctx.stroke();
    }

    // --- energy shield segments (horizontal arcs) ---
    for (let i = 1; i <= 3; i++) {
      const frac = i / 4;
      const arcH = domeH * frac;
      const arcW = domeW * Math.sqrt(1 - Math.pow(1 - frac, 2));
      ctx.beginPath();
      ctx.ellipse(x, baseY, arcW, arcH, 0, Math.PI, 0, true);
      ctx.stroke();
    }

    // --- shield generator at apex (diamond shape) ---
    const lightY = baseY - domeH;
    const lightPulse = 0.5 + Math.sin(time * 2) * 0.15;
    glow(ctx, x, lightY, 20, C.energyCyan, lightPulse);

    // diamond shape instead of circle
    ctx.fillStyle = C.energyCyan;
    ctx.beginPath();
    ctx.moveTo(x, lightY - 5);
    ctx.lineTo(x + 4, lightY);
    ctx.lineTo(x, lightY + 5);
    ctx.lineTo(x - 4, lightY);
    ctx.closePath();
    ctx.fill();

    // rays upward from shield generator
    ctx.strokeStyle = rgba(C.energyCyan, 0.12);
    ctx.lineWidth = 1;
    for (let i = 0; i < 8; i++) {
      const angle = Math.PI * 1.1 + (i / 7) * Math.PI * 0.8;
      ctx.beginPath();
      ctx.moveTo(x, lightY);
      ctx.lineTo(x + Math.cos(angle) * domeW * 0.5, lightY + Math.sin(angle) * domeH * 0.6);
      ctx.stroke();
    }

    // --- shield sheen (subtle highlight arc, cyan tint) ---
    ctx.strokeStyle = rgba(C.energyCyan, 0.06);
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.ellipse(x - domeW * 0.2, baseY, domeW * 0.5, domeH * 0.85, -0.15, Math.PI * 1.2, Math.PI * 1.7, false);
    ctx.stroke();

    ctx.restore();
  }


  // ==========================================================================
  // 7.  STARFIELD  (background particles)
  // ==========================================================================
  //
  //  Three depth layers. Each star twinkles on its own cycle.
  //  Stars are seeded deterministically so positions stay stable across frames.
  //
  function drawStarfield(ctx, width, height, options) {
    options = options || {};
    const count = options.starCount || 120;
    const time  = options.time || 0;

    const rng = seededRand(42);

    for (let i = 0; i < count; i++) {
      const sx = rng() * width;
      const sy = rng() * height;
      const layer = Math.floor(rng() * 3);   // 0=far, 1=mid, 2=near
      const twinklePhase = rng() * Math.PI * 2;
      const twinkleSpeed = 0.6 + rng() * 1.4;

      let pxSize, baseAlpha;
      switch (layer) {
        case 0:  pxSize = 0.6;  baseAlpha = 0.25; break;
        case 1:  pxSize = 1.0;  baseAlpha = 0.45; break;
        default: pxSize = 1.5;  baseAlpha = 0.65; break;
      }

      const alpha = baseAlpha + Math.sin(time * twinkleSpeed + twinklePhase) * baseAlpha * 0.5;
      ctx.fillStyle = rgba(C.white, Math.max(0, alpha));
      ctx.fillRect(Math.floor(sx), Math.floor(sy), pxSize, pxSize);

      // near-layer stars get a tiny cross-shaped sparkle
      if (layer === 2 && alpha > 0.6) {
        ctx.fillStyle = rgba(C.white, (alpha - 0.6) * 0.8);
        ctx.fillRect(Math.floor(sx) - 1, Math.floor(sy), 3, 1);
        ctx.fillRect(Math.floor(sx), Math.floor(sy) - 1, 1, 3);
      }
    }
  }


  // ==========================================================================
  // 8.  POD TRAIL  (glowing trail behind moving pods)
  // ==========================================================================
  //
  //  Draws a series of circles with decreasing alpha behind the pod.
  //  velX, velY give the direction of travel (trail goes opposite).
  //
  function drawPodTrail(ctx, x, y, velX, velY, color, options) {
    options = options || {};
    const segments = options.trailLength || 12;
    const spacing  = options.spacing || 3;

    // normalize direction
    const mag = Math.sqrt(velX * velX + velY * velY) || 1;
    const dx = (velX / mag) * spacing;
    const dy = (velY / mag) * spacing;

    for (let i = 1; i <= segments; i++) {
      const t = i / segments;
      const tx = x - dx * i;
      const ty = y - dy * i;
      const r = (1 - t * 0.7) * 3;
      const a = (1 - t) * 0.5;

      ctx.fillStyle = rgba(color, a);
      ctx.beginPath();
      ctx.arc(tx, ty, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }


  // ==========================================================================
  // 9.  BRAIN PULSE EFFECT  (retrain / learning event)
  // ==========================================================================
  //
  //  progress: 0 (just fired) -> 1 (fully faded)
  //  Expanding ring + particle burst + central flash.
  //
  function drawBrainPulse(ctx, x, y, progress, options) {
    options = options || {};
    const maxR = options.maxRadius || 120;
    const ringR = progress * maxR;
    const fade = 1 - progress;

    ctx.save();

    // --- central flash (early phase only) ---
    if (progress < 0.25) {
      const flashA = (0.25 - progress) / 0.25;
      glow(ctx, x, y, 35, C.white, flashA * 0.9);
    }

    // --- expanding ring 1 (white, thin) ---
    ctx.strokeStyle = rgba(C.white, fade * 0.6);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, ringR, 0, Math.PI * 2);
    ctx.stroke();

    // --- expanding ring 2 (amber, wider) ---
    ctx.strokeStyle = rgba(C.amber, fade * 0.5);
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.arc(x, y, ringR * 0.95, 0, Math.PI * 2);
    ctx.stroke();

    // --- expanding ring 3 (amber glow, very wide) ---
    ctx.strokeStyle = rgba(C.amber, fade * 0.15);
    ctx.lineWidth = 14;
    ctx.beginPath();
    ctx.arc(x, y, ringR * 0.9, 0, Math.PI * 2);
    ctx.stroke();

    // --- particle burst ---
    const pCount = 24;
    for (let i = 0; i < pCount; i++) {
      const angle = (i / pCount) * Math.PI * 2;
      // spiral outward with some randomness baked into angle
      const spread = 1 + Math.sin(i * 7.3) * 0.3;
      const dist = progress * maxR * 0.75 * spread;
      const px = x + Math.cos(angle) * dist;
      const py = y + Math.sin(angle) * dist;
      const pSize = fade * 2.5 * (0.5 + Math.sin(i * 4.7) * 0.5);
      const pAlpha = fade * 0.7;

      // alternate white and amber particles
      const pColor = (i % 3 === 0) ? C.white : C.amber;
      ctx.fillStyle = rgba(pColor, pAlpha);
      ctx.beginPath();
      ctx.arc(px, py, Math.max(0.3, pSize), 0, Math.PI * 2);
      ctx.fill();
    }

    // --- secondary ring (delayed, for ripple feel) ---
    if (progress > 0.15) {
      const p2 = (progress - 0.15) / 0.85;
      const r2 = p2 * maxR * 0.8;
      const fade2 = 1 - p2;
      ctx.strokeStyle = rgba(C.amber, fade2 * 0.25);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, r2, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.restore();
  }


  // ==========================================================================
  // 10. PATTERN CARD ICONS  (12x12 pixel art, 5 types)
  // ==========================================================================

  function drawPatternIcon(ctx, x, y, patternType, size, options) {
    size = size || 1;
    const s = size;
    const bx = x - 6 * s;
    const by = y - 6 * s;

    switch (patternType) {

      // --- WASH RING: circular arrows ---
      case 'wash_ring': {
        // outer circle
        pxBatch(ctx, bx, by, s, C.podBlue, [
          [4,0],[5,0],[6,0],[7,0],
          [2,1],[3,1],               [8,1],[9,1],
          [1,2],                          [10,2],
          [0,3],                               [11,3],
          [0,4],                               [11,4],
          [0,5],                               [11,5],
          [0,6],                               [11,6],
          [0,7],                               [11,7],
          [1,8],                          [10,8],
          [2,9],[3,9],               [8,9],[9,9],
          [4,10],[5,10],[6,10],[7,10],
        ]);
        // arrowheads
        pxBatch(ctx, bx, by, s, C.white, [
          [8,0],[9,0],[10,1],       // top-right arrow
          [1,10],[2,10],[3,9],      // bottom-left arrow
        ]);
        break;
      }

      // --- VELOCITY: lightning bolt ---
      case 'velocity': {
        pxBatch(ctx, bx, by, s, C.amber, [
                        [7,0],[8,0],
                   [6,1],[7,1],
              [5,2],[6,2],
         [4,3],[5,3],[6,3],[7,3],[8,3],[9,3],
                        [7,4],[8,4],
                   [6,5],[7,5],
              [5,6],[6,6],
         [4,7],[5,7],
         [3,8],[4,8],
         [2,9],[3,9],
              [3,10],
        ]);
        // highlight
        pxBatch(ctx, bx, by, s, C.amberLight, [
          [7,0],[6,1],[5,2],
        ]);
        break;
      }

      // --- UNAUTHORIZED TRANSFER: theatre mask ---
      case 'unauthorized_transfer': {
        // mask body
        pxBatch(ctx, bx, by, s, C.petalPurple, [
              [3,0],[4,0],[5,0],[6,0],[7,0],[8,0],
         [2,1],[3,1],[4,1],[5,1],[6,1],[7,1],[8,1],[9,1],
         [1,2],[2,2],[3,2],               [8,2],[9,2],[10,2],
         [1,3],[2,3],                          [9,3],[10,3],
         [1,4],[2,4],                          [9,4],[10,4],
         [1,5],[2,5],[3,5],               [8,5],[9,5],[10,5],
              [3,6],[4,6],[5,6],[6,6],[7,6],[8,6],
                   [4,7],[5,7],[6,7],[7,7],
                        [5,8],[6,8],
        ]);
        // eye holes
        pxBatch(ctx, bx, by, s, C.deepSpace, [
          [4,2],[5,2],    [6,2],[7,2],      // left eye, right eye
          [4,3],[5,3],    [6,3],[7,3],
        ]);
        // eye glints
        pxBatch(ctx, bx, by, s, C.white, [
          [4,2],[7,2],
        ]);
        // smile
        pxBatch(ctx, bx, by, s, C.deepSpace, [
          [4,5],[5,6],[6,6],[7,5],
        ]);
        break;
      }

      // --- STRUCTURING: grid of blocks (broken into sub-amounts) ---
      case 'structuring': {
        const blockColor = C.clearGreen;
        const blockShadow = C.clearGreenShadow;
        // 3x3 grid of 2x2 blocks with gaps
        const offsets = [[0,0],[4,0],[8,0],[0,4],[4,4],[8,4],[0,8],[4,8],[8,8]];
        offsets.forEach(([ox, oy]) => {
          pxBatch(ctx, bx, by, s, blockColor, [
            [1+ox, 1+oy],[2+ox, 1+oy],
            [1+ox, 2+oy],[2+ox, 2+oy],
          ]);
          // shadow bottom-right
          pxBatch(ctx, bx, by, s, blockShadow, [
            [2+ox, 2+oy],[3+ox, 2+oy],[3+ox, 1+oy],
          ]);
        });
        break;
      }

      // --- HUB: central node with radiating connections ---
      case 'hub': {
        // center node (larger)
        pxBatch(ctx, bx, by, s, C.threatRed, [
          [5,4],[6,4],[5,5],[6,5],[5,6],[6,6],
        ]);
        // spokes
        pxBatch(ctx, bx, by, s, C.threatRedShadow, [
          // vertical
          [5,2],[6,2],[5,3],[6,3],
          [5,7],[6,7],[5,8],[6,8],
          // horizontal
          [2,5],[3,5],[3,6],[2,6],
          [8,5],[9,5],[8,6],[9,6],
          // diagonals
          [3,3],[4,4],
          [8,3],[7,4],
          [3,8],[4,7],
          [8,8],[7,7],
        ]);
        // outer nodes
        pxBatch(ctx, bx, by, s, C.threatRed, [
          [5,0],[6,0],[5,1],[6,1],       // top
          [5,10],[6,10],[5,9],[6,9],     // bottom
          [0,5],[0,6],[1,5],[1,6],       // left
          [10,5],[10,6],[11,5],[11,6],   // right
          [1,1],[2,2],                   // top-left
          [10,1],[9,2],                  // top-right
          [1,10],[2,9],                  // bottom-left
          [10,10],[9,9],                 // bottom-right
        ]);
        break;
      }

      default:
        // fallback: question mark
        pxBatch(ctx, bx, by, s, C.white, [
          [4,1],[5,1],[6,1],[7,1],
          [8,2],[8,3],
          [6,4],[7,4],
          [5,5],[6,5],
          [5,6],
          [5,8],
        ]);
    }
  }


  // ==========================================================================
  // 11. BONUS SPRITES
  // ==========================================================================

  // --- Dot Grid (for the background, matching the Stitch mockup) ---
  function drawDotGrid(ctx, width, height, options) {
    options = options || {};
    const spacing = options.spacing || 30;
    const dotSize = options.dotSize || 1;
    const color   = options.color || rgba(C.white, 0.08);
    ctx.fillStyle = color;
    for (let gx = spacing; gx < width; gx += spacing) {
      for (let gy = spacing; gy < height; gy += spacing) {
        ctx.fillRect(gx, gy, dotSize, dotSize);
      }
    }
  }

  // --- Scan-line CRT overlay (very subtle) ---
  function drawScanlines(ctx, width, height, options) {
    options = options || {};
    const alpha = options.alpha || 0.04;
    ctx.fillStyle = rgba('#000000', alpha);
    for (let sy = 0; sy < height; sy += 4) {
      ctx.fillRect(0, sy, width, 2);
    }
  }

  // --- Floating label / tag for a pod (e.g., "TRD-91") ---
  function drawPodLabel(ctx, x, y, text, color, size) {
    size = size || 1;
    ctx.save();
    ctx.font = `${Math.round(10 * size)}px "VT323", "Courier New", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = rgba(color || C.white, 0.7);
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  // --- Mini sparkle (for landing / transformation effects) ---
  function drawSparkle(ctx, x, y, size, progress, color) {
    color = color || C.white;
    const fade = 1 - progress;
    const r = size * (0.5 + progress * 1.5);
    const a = fade * 0.8;

    ctx.save();
    ctx.strokeStyle = rgba(color, a);
    ctx.lineWidth = 1;

    // 4 lines forming a + shape
    ctx.beginPath();
    ctx.moveTo(x - r, y); ctx.lineTo(x + r, y);
    ctx.moveTo(x, y - r); ctx.lineTo(x, y + r);
    ctx.stroke();

    // 4 lines forming an X shape (smaller)
    const r2 = r * 0.6;
    ctx.beginPath();
    ctx.moveTo(x - r2, y - r2); ctx.lineTo(x + r2, y + r2);
    ctx.moveTo(x + r2, y - r2); ctx.lineTo(x - r2, y + r2);
    ctx.stroke();

    ctx.restore();
  }

  // --- Status indicator ring (wraps around a pod or icon) ---
  function drawStatusRing(ctx, x, y, radius, color, options) {
    options = options || {};
    const lineWidth = options.lineWidth || 2;
    const dashPhase = options.dashPhase || 0;
    const dashed    = options.dashed !== false;

    ctx.save();
    ctx.strokeStyle = rgba(color, 0.6);
    ctx.lineWidth = lineWidth;
    if (dashed) {
      ctx.setLineDash([4, 3]);
      ctx.lineDashOffset = dashPhase;
    }
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }

  // --- Landing burst (when pod lands in fortress) ---
  function drawLandingBurst(ctx, x, y, progress, options) {
    options = options || {};
    const maxR = options.maxRadius || 30;
    const color = options.color || C.clearGreen;
    const fade = 1 - progress;

    // ring
    ctx.strokeStyle = rgba(color, fade * 0.5);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, progress * maxR, 0, Math.PI * 2);
    ctx.stroke();

    // ground scatter particles (falling downward)
    const pCount = 8;
    for (let i = 0; i < pCount; i++) {
      const angle = (i / pCount) * Math.PI * 2;
      const dist = progress * maxR * 0.6;
      const px2 = x + Math.cos(angle) * dist;
      const py2 = y + Math.sin(angle) * dist * 0.5 + progress * 5;
      const pSize = fade * 2;
      ctx.fillStyle = rgba(color, fade * 0.6);
      ctx.fillRect(px2, py2, pSize, pSize);
    }
  }

  // --- Metric bar (small horizontal bar for panels) ---
  function drawMetricBar(ctx, x, y, width, height, fillRatio, color, bgColor) {
    bgColor = bgColor || rgba(C.panelDark, 0.8);
    ctx.fillStyle = bgColor;
    ctx.fillRect(x, y, width, height);
    ctx.fillStyle = color;
    ctx.fillRect(x, y, width * Math.min(1, fillRatio), height);
    // border
    ctx.strokeStyle = rgba(C.white, 0.1);
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, width, height);
  }


  // ==========================================================================
  // 12. COMPOSITE SCENE HELPERS
  // ==========================================================================

  /**
   * Draw a complete pod with trail, label, and status ring.
   * podType: 'neutral' | 'flagged' | 'clear'
   */
  function drawPodComplete(ctx, x, y, size, podType, options) {
    options = options || {};
    const time = options.time || 0;
    const velX = options.velX || 0;
    const velY = options.velY || 0;
    const label = options.label || '';

    // determine color for trail
    let trailColor;
    switch (podType) {
      case 'flagged': trailColor = C.threatRed; break;
      case 'clear':   trailColor = C.clearGreen; break;
      default:        trailColor = C.podBlue; break;
    }

    // trail (if moving)
    if (Math.abs(velX) + Math.abs(velY) > 0.1) {
      drawPodTrail(ctx, x, y, velX, velY, trailColor, { trailLength: 10 });
    }

    // pod body
    switch (podType) {
      case 'flagged': drawCargoPodFlagged(ctx, x, y, size, { time, shake: 2 }); break;
      case 'clear':   drawCargoPodClear(ctx, x, y, size); break;
      default:        drawCargoPodNeutral(ctx, x, y, size); break;
    }

    // label below
    if (label) {
      drawPodLabel(ctx, x, y + 10 * size, label, trailColor, size * 0.9);
    }
  }

  /**
   * Draw a defense turret at a given stage (0-3).
   * stage 0=base, 1=activating, 2=online, 3=full power
   */
  function drawDefenseAtStage(ctx, x, y, size, stage, options) {
    options = options || {};
    switch (stage) {
      case 0: drawTurretBase(ctx, x, y, size, options); break;
      case 1: drawTurretActivating(ctx, x, y, size, options); break;
      case 2: drawTurretOnline(ctx, x, y, size, options); break;
      default: drawTurretFullPower(ctx, x, y, size, options); break;
    }
  }

  /**
   * Draw a full fortress scene (dome + multiple turrets).
   * turrets: array of { x, y, stage, petalColor }
   */
  function drawFortressScene(ctx, x, y, width, height, turrets, options) {
    options = options || {};
    const time = options.time || 0;

    // dome first (background)
    drawFortressDome(ctx, x, y, width, height, { time });

    // turrets on top
    const turretSize = options.plantSize || 2;
    const baseY = y + height * 0.5;
    (turrets || []).forEach(p => {
      drawDefenseAtStage(ctx, p.x, baseY - 8 * turretSize, turretSize, p.stage, {
        time,
        petalColor: p.petalColor,
      });
    });
  }


  // ==========================================================================
  // PUBLIC API
  // ==========================================================================
  return {
    // Palette
    colors: C,

    // Helpers (exposed for advanced usage)
    helpers: { px, pxBatch, rgba, glow, seededRand, lerpColor },

    // Pod sprites
    drawCargoPodNeutral,
    drawCargoPodFlagged,
    drawCargoPodClear,
    drawPodTrail,
    drawPodComplete,

    // Defense grid
    drawDefenseGrid,
    drawDeathStar,
    drawEarth,
    drawSatellite,

    // Defense turret sprites (individual stages)
    drawTurretBase,
    drawTurretActivating,
    drawTurretOnline,
    drawTurretFullPower,
    drawDefenseAtStage,

    // Fortress dome
    drawFortressDome,
    drawFortressScene,

    // Backward-compat aliases (old botanical names)
    drawPlantSeed:      drawTurretBase,
    drawPlantSprout:    drawTurretActivating,
    drawPlantGrowing:   drawTurretOnline,
    drawPlantBloom:     drawTurretFullPower,
    drawPlantAtStage:   drawDefenseAtStage,
    drawGreenhouseDome: drawFortressDome,
    drawGreenhouseScene:drawFortressScene,

    // Starfield & atmosphere
    drawStarfield,
    drawDotGrid,
    drawScanlines,

    // Effects
    drawBrainPulse,
    drawLandingBurst,
    drawSparkle,
    drawStatusRing,

    // Pattern icons
    drawPatternIcon,

    // UI elements
    drawPodLabel,
    drawMetricBar,
  };

})();

// CommonJS export for bundlers; also works as a global in browsers
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PixelSprites;
}
