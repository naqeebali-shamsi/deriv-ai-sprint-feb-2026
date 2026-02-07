// ============================================================================
// PixelSprites.js -- Orbital Greenhouse Pixel Art Sprite System
// ============================================================================
// All visual assets for the Orbital Greenhouse fraud detection canvas.
// Drawn programmatically with Canvas 2D -- zero external images.
//
// Aesthetic: Stardew Valley warmth meets Hyper Light Drifter glow.
// Palette:   Lospec "Cozy" inspired (see PALETTE below).
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
    plantGreen:     '#5b8c5a',
    plantGreenLight:'#7dba7b',
    darkGreen:      '#3a6b3a',
    threatRed:      '#ef4444',
    threatRedShadow:'#b91c1c',
    threatRedDark:  '#991b1b',
    amber:          '#ffb94f',
    darkAmber:      '#c98a2e',
    amberLight:     '#ffd080',
    soilBrown:      '#6b4c2a',
    darkSoil:       '#4a3420',
    richSoil:       '#5c3d1e',
    petalRed:       '#e06060',
    petalPurple:    '#9b6dff',
    petalYellow:    '#ffd700',
    petalPink:      '#f0a0c0',
    white:          '#f5f0e1',
    whiteDim:       '#c0b8a4',
    potTerracotta:  '#b86f50',
    potShadow:      '#8b5638',
    potRim:         '#d4956a',
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
  // 4.  DEFENSE GRID RING
  // ==========================================================================
  //
  //  Concentric circles + scanning beam + pixel-art shield at center.
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

    // -- shield icon at center (pixel art, 13x14) --
    const ss = Math.max(1.2, radius / 80);  // scale shield relative to grid
    const sx = x - 6 * ss;
    const sy = y - 7 * ss;

    // shield body
    pxBatch(ctx, sx, sy, ss, C.amber, [
                        [5,0],[6,0],[7,0],
                   [3,1],[4,1],[5,1],[6,1],[7,1],[8,1],[9,1],
              [2,2],[3,2],[4,2],[5,2],[6,2],[7,2],[8,2],[9,2],[10,2],
         [1,3],[2,3],[3,3],[4,3],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,3],
         [1,4],[2,4],[3,4],[4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],
         [1,5],[2,5],[3,5],[4,5],[5,5],[6,5],[7,5],[8,5],[9,5],[10,5],[11,5],
         [1,6],[2,6],[3,6],[4,6],[5,6],[6,6],[7,6],[8,6],[9,6],[10,6],[11,6],
              [2,7],[3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7],[10,7],
              [2,8],[3,8],[4,8],[5,8],[6,8],[7,8],[8,8],[9,8],[10,8],
                   [3,9],[4,9],[5,9],[6,9],[7,9],[8,9],[9,9],
                        [4,10],[5,10],[6,10],[7,10],[8,10],
                             [5,11],[6,11],[7,11],
                                  [6,12],
    ]);

    // shield highlight
    pxBatch(ctx, sx, sy, ss, C.amberLight, [
      [5,1],[6,1],[7,1],
      [3,2],[4,2],[5,2],
      [2,3],[3,3],
      [1,4],[2,4],
    ]);

    // shield dark edge
    pxBatch(ctx, sx, sy, ss, C.darkAmber, [
      [10,3],[11,3],
      [10,4],[11,4],
      [10,5],[11,5],
      [10,6],[11,6],
      [9,7],[10,7],
      [9,8],[10,8],
      [8,9],[9,9],
      [7,10],[8,10],
      [6,11],[7,11],
      [6,12],
    ]);

    // shield inner cross
    pxBatch(ctx, sx, sy, ss, C.darkAmber, [
      [6,3],[6,4],[6,5],[6,6],[6,7],[6,8],[6,9],[6,10],
      [3,6],[4,6],[5,6],[6,6],[7,6],[8,6],[9,6],
    ]);
  }


  // ==========================================================================
  // 5.  PLANT GROWTH STAGES  (4 frames, each 16x16)
  // ==========================================================================

  // -- Shared: terracotta planter pot (bottom of each plant sprite) --
  function _drawPot(ctx, bx, by, s) {
    // pot rim
    pxBatch(ctx, bx, by, s, C.potRim, [
      [3,11],[4,11],[5,11],[6,11],[7,11],[8,11],[9,11],[10,11],[11,11],[12,11],
    ]);
    // pot body
    pxBatch(ctx, bx, by, s, C.potTerracotta, [
      [4,12],[5,12],[6,12],[7,12],[8,12],[9,12],[10,12],[11,12],
      [4,13],[5,13],[6,13],[7,13],[8,13],[9,13],[10,13],[11,13],
      [5,14],[6,14],[7,14],[8,14],[9,14],[10,14],
    ]);
    // pot shadow
    pxBatch(ctx, bx, by, s, C.potShadow, [
      [9,12],[10,12],[11,12],
      [9,13],[10,13],[11,13],
      [9,14],[10,14],
    ]);
    // soil inside pot
    pxBatch(ctx, bx, by, s, C.soilBrown, [
      [5,11],[6,11],[7,11],[8,11],[9,11],[10,11],
    ]);
    pxBatch(ctx, bx, by, s, C.darkSoil, [
      [6,11],[8,11],
    ]);
  }

  // 5a. SEED -- small brown seed with crack, resting on soil in pot
  function drawPlantSeed(ctx, x, y, size, options) {
    size = size || 1;
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;

    _drawPot(ctx, bx, by, s);

    // seed body
    pxBatch(ctx, bx, by, s, C.darkSoil, [
      [7,9],[8,9],
      [7,10],[8,10],
    ]);
    pxBatch(ctx, bx, by, s, C.soilBrown, [
      [7,9],
    ]);
    // crack highlight
    pxBatch(ctx, bx, by, s, C.richSoil, [
      [8,9],
    ]);
    // tiny sprout hint (barely visible green dot)
    pxBatch(ctx, bx, by, s, rgba(C.plantGreen, 0.5), [
      [7,8],
    ]);
  }

  // 5b. SPROUT -- thin stem with 2 tiny cotyledon leaves
  function drawPlantSprout(ctx, x, y, size, options) {
    size = size || 1;
    options = options || {};
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;
    const t = options.time || 0;
    const sway = Math.sin(t * 2) * 0.3;  // gentle sway

    _drawPot(ctx, bx, by, s);

    // stem
    pxBatch(ctx, bx, by, s, C.darkGreen, [
      [7,10],[7,9],[7,8],[7,7],
    ]);

    // cotyledon leaves (two small rounded leaves)
    pxBatch(ctx, bx, by, s, C.plantGreen, [
      [5,7],[6,7],          // left leaf
      [8,6],[9,6],          // right leaf
    ]);
    pxBatch(ctx, bx, by, s, C.plantGreenLight, [
      [6,7],                // left highlight
      [8,6],                // right highlight
    ]);
  }

  // 5c. PLANT -- fuller bush, 3-4 leaves, small flower bud
  function drawPlantGrowing(ctx, x, y, size, options) {
    size = size || 1;
    options = options || {};
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;

    _drawPot(ctx, bx, by, s);

    // main stem
    pxBatch(ctx, bx, by, s, C.darkGreen, [
      [7,10],[7,9],[7,8],[7,7],[7,6],[7,5],
    ]);
    // branch stems
    pxBatch(ctx, bx, by, s, C.darkGreen, [
      [6,8],[5,7],          // left branch
      [8,7],[9,6],          // right branch
    ]);

    // leaves (bushy)
    pxBatch(ctx, bx, by, s, C.plantGreen, [
      [4,7],[5,7],[6,7],              // left cluster
      [8,6],[9,6],[10,6],             // right cluster
      [5,5],[6,5],                    // upper left
      [8,5],[9,5],                    // upper right
      [4,8],[5,8],                    // lower left
      [9,7],[10,7],                   // lower right
    ]);
    // leaf highlights
    pxBatch(ctx, bx, by, s, C.plantGreenLight, [
      [5,7],[6,5],[8,5],[9,6],
    ]);

    // flower bud
    pxBatch(ctx, bx, by, s, C.darkAmber, [
      [7,4],[8,4],
      [7,3],
    ]);
    pxBatch(ctx, bx, by, s, C.amber, [
      [7,3],
    ]);
  }

  // 5d. BLOOM -- full plant with colorful flower, many leaves
  function drawPlantBloom(ctx, x, y, size, options) {
    size = size || 1;
    options = options || {};
    const s = size;
    const bx = x - 8 * s;
    const by = y - 8 * s;
    const petal = options.petalColor || C.petalRed;
    const t = options.time || 0;
    const sway = Math.sin(t * 1.5) * 0.15;

    _drawPot(ctx, bx, by, s);

    // main stem
    pxBatch(ctx, bx, by, s, C.darkGreen, [
      [7,10],[7,9],[7,8],[7,7],[7,6],[7,5],[7,4],
    ]);
    // branch stems
    pxBatch(ctx, bx, by, s, C.darkGreen, [
      [6,9],[5,8],[4,7],
      [8,8],[9,7],[10,6],
    ]);

    // full foliage
    pxBatch(ctx, bx, by, s, C.plantGreen, [
      [3,8],[4,8],[5,8],[6,8],              // left mid
      [8,7],[9,7],[10,7],[11,7],            // right mid
      [4,6],[5,6],[6,6],                    // upper left
      [8,5],[9,5],[10,5],                   // upper right
      [3,9],[4,9],[5,9],                    // lower left
      [9,8],[10,8],[11,8],                  // lower right
      [5,10],[6,10],                        // base left
      [8,10],[9,10],                        // base right
    ]);
    // leaf highlights
    pxBatch(ctx, bx, by, s, C.plantGreenLight, [
      [4,8],[5,6],[6,6],[8,5],[9,5],[4,9],[9,7],[10,7],
    ]);
    // leaf shadows (depth)
    pxBatch(ctx, bx, by, s, C.darkGreen, [
      [3,9],[11,8],[5,10],[9,10],
    ]);

    // --- FLOWER ---
    // petals (star/cross arrangement)
    pxBatch(ctx, bx, by, s, petal, [
                   [7,0],                        // top
              [6,1],[7,1],[8,1],                  // upper ring
         [5,2],[6,2],     [8,2],[9,2],            // mid (gap for center)
              [5,3],            [9,3],            // sides
         [5,4],[6,4],     [8,4],[9,4],            // lower ring
    ]);
    // petal highlight
    pxBatch(ctx, bx, by, s, rgba(C.white, 0.3), [
      [6,1],[7,0],
    ]);

    // flower center (warm yellow)
    pxBatch(ctx, bx, by, s, C.petalYellow, [
      [7,2],[7,3],
    ]);
    pxBatch(ctx, bx, by, s, C.amber, [
      [6,3],[8,3],
    ]);
  }


  // ==========================================================================
  // 6.  GREENHOUSE DOME
  // ==========================================================================
  //
  //  Semi-circular dome with glass panel grid, amber grow-light,
  //  warm interior gradient.  Drawn behind the plants.
  //
  function drawGreenhouseDome(ctx, x, y, width, height, options) {
    options = options || {};
    const time = options.time || 0;
    ctx.save();

    const domeW = width * 0.5;
    const domeH = height * 0.45;
    const baseY = y + height * 0.5;

    // --- warm interior glow ---
    const interiorGrad = ctx.createRadialGradient(x, baseY - domeH * 0.3, 0, x, baseY - domeH * 0.3, domeW);
    interiorGrad.addColorStop(0, rgba(C.amber, 0.15));
    interiorGrad.addColorStop(0.5, rgba(C.amber, 0.06));
    interiorGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = interiorGrad;
    ctx.beginPath();
    ctx.ellipse(x, baseY, domeW, domeH, 0, Math.PI, 0, true);
    ctx.fill();

    // --- dome outline ---
    ctx.strokeStyle = rgba(C.spaceBlue, 0.5);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(x, baseY, domeW, domeH, 0, Math.PI, 0, true);
    ctx.stroke();

    // --- base platform ---
    ctx.strokeStyle = rgba(C.amber, 0.3);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x - domeW - 10, baseY);
    ctx.lineTo(x + domeW + 10, baseY);
    ctx.stroke();

    // --- glass panel grid (vertical ribs) ---
    ctx.strokeStyle = rgba(C.spaceBlue, 0.2);
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

    // --- glass panel grid (horizontal arcs) ---
    for (let i = 1; i <= 3; i++) {
      const frac = i / 4;
      const arcH = domeH * frac;
      const arcW = domeW * Math.sqrt(1 - Math.pow(1 - frac, 2));
      ctx.beginPath();
      ctx.ellipse(x, baseY, arcW, arcH, 0, Math.PI, 0, true);
      ctx.stroke();
    }

    // --- grow-light at apex ---
    const lightY = baseY - domeH;
    const lightPulse = 0.5 + Math.sin(time * 2) * 0.15;
    glow(ctx, x, lightY, 20, C.amber, lightPulse);

    ctx.fillStyle = C.amber;
    ctx.beginPath();
    ctx.arc(x, lightY, 4, 0, Math.PI * 2);
    ctx.fill();

    // light rays downward
    ctx.strokeStyle = rgba(C.amber, 0.12);
    ctx.lineWidth = 1;
    for (let i = 0; i < 12; i++) {
      const angle = Math.PI * 0.15 + (i / 11) * Math.PI * 0.7;
      ctx.beginPath();
      ctx.moveTo(x, lightY);
      ctx.lineTo(x + Math.cos(angle) * domeW * 0.7, lightY + Math.sin(angle) * domeH * 0.8);
      ctx.stroke();
    }

    // --- glass sheen (subtle highlight arc) ---
    ctx.strokeStyle = rgba(C.white, 0.08);
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

      // --- SPOOFING: theatre mask ---
      case 'spoofing': {
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

  // --- Landing burst (when pod lands in greenhouse) ---
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
   * Draw a plant at a given growth stage (0-3).
   * stage 0=seed, 1=sprout, 2=growing, 3=bloom
   */
  function drawPlantAtStage(ctx, x, y, size, stage, options) {
    options = options || {};
    switch (stage) {
      case 0: drawPlantSeed(ctx, x, y, size, options); break;
      case 1: drawPlantSprout(ctx, x, y, size, options); break;
      case 2: drawPlantGrowing(ctx, x, y, size, options); break;
      default: drawPlantBloom(ctx, x, y, size, options); break;
    }
  }

  /**
   * Draw a full greenhouse scene (dome + multiple plants).
   * plants: array of { x, y, stage, petalColor }
   */
  function drawGreenhouseScene(ctx, x, y, width, height, plants, options) {
    options = options || {};
    const time = options.time || 0;

    // dome first (background)
    drawGreenhouseDome(ctx, x, y, width, height, { time });

    // plants on top
    const plantSize = options.plantSize || 2;
    const baseY = y + height * 0.5;
    (plants || []).forEach(p => {
      drawPlantAtStage(ctx, p.x, baseY - 8 * plantSize, plantSize, p.stage, {
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

    // Plant sprites (individual stages)
    drawPlantSeed,
    drawPlantSprout,
    drawPlantGrowing,
    drawPlantBloom,
    drawPlantAtStage,

    // Greenhouse
    drawGreenhouseDome,
    drawGreenhouseScene,

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
