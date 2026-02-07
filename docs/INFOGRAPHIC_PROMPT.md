# Infographic Generation Prompt

Use this prompt with Nanobanaa Pro to generate a ByteByteGo-style architecture diagram.

---

## Prompt

```
Create a clean, professional system architecture infographic in the ByteByteGo visual style — orthogonal layout, rounded-rectangle components, color-coded sections, clean data flow arrows with labels, light background, and minimal icons.

Title at the top: "Autonomous Fraud Detection Agent"
Subtitle: "Real-time scoring, self-improving ML, LLM-powered investigation"

The diagram shows 5 horizontally-arranged layers flowing left to right, connected by labeled arrows:

LAYER 1 — INGESTION (Blue #3B82F6):
- Icon: streaming waves
- Box: "Transaction Simulator"
- Small label: "5 fraud typologies | 1 TPS continuous stream"
- Arrow labeled "JSON" pointing right to Layer 2

LAYER 2 — SCORING ENGINE (Purple #8B5CF6):
- Two stacked boxes:
  - Top: "Feature Engine" with label "17 features: velocity, amount, temporal, channel"
  - Bottom: "ML Model" with label "GradientBoosting | scikit-learn | versioned"
- Arrow between them labeled "feature vector → probability"
- Small decision diamond: ">0.5 review | >0.8 block"
- Arrow labeled "risk score" pointing right to Layer 3

LAYER 3 — CASE MANAGEMENT (Red #EF4444):
- Two stacked boxes:
  - Top: "Auto-Case Creator" with label "Cases open automatically for flagged txns"
  - Bottom: "AI Explainer" with label "Llama 3.1:8b (local via Ollama)"
- Arrow labeled "explanation" pointing right to Layer 4

LAYER 4 — LEARNING LOOP (Green #10B981):
- Three stacked boxes:
  - Top: "Analyst Review" with label "Label: fraud / legitimate"
  - Middle: "Model Trainer" with label "Retrain → new version"
  - Bottom: "Metrics Tracker" with label "Precision | Recall | F1 trend"
- IMPORTANT: A bold curved arrow from "Model Trainer" looping BACK to "ML Model" in Layer 2, labeled "feedback loop — model improves" — this is the key visual showing the self-improving cycle

LAYER 5 — PATTERN MINING (Amber #F59E0B):
- Sits BELOW the main flow (not inline)
- Box: "Graph Mining Engine" with label "NetworkX | 4 algorithms"
- Four small pill-shaped badges inside: "Rings", "Hubs", "Velocity Spikes", "Dense Clusters"
- Arrow from database going down to this box
- Arrow from this box going back up to Layer 3 labeled "pattern cards"

DATABASE (Gray #6B7280):
- Cylinder icon sitting below Layers 2-3
- Label: "SQLite | 6 tables | Indexed | WAL mode"
- Thin arrows connecting to Layers 2, 3, 4, and 5

BOTTOM BAR — Tech Stack:
- Horizontal strip at the very bottom
- Logos/text: "Python | FastAPI | Streamlit | scikit-learn | NetworkX | Ollama | SQLite"

VISUAL STYLE REQUIREMENTS:
- ByteByteGo aesthetic: clean, professional, light gray (#FAFAFA) background
- Rounded rectangles with subtle drop shadows
- Each layer has a distinct color with white text
- Arrows are clean with rounded corners, labeled at midpoint
- The feedback loop arrow (green, from Trainer back to ML Model) should be the most prominent visual element — this is what makes the system "self-improving"
- Small icons in each box (gear for engine, brain for ML, shield for cases, chart for metrics, network for graph)
- No clutter — whitespace between components
- Professional font, hierarchy: title > section headers > component names > labels
- Aspect ratio: 16:9 landscape
```

---

## Alternative Shorter Prompt (if the tool has length limits)

```
ByteByteGo-style system architecture diagram, clean orthogonal layout, light background, 16:9 landscape.

Title: "Autonomous Fraud Detection Agent"

5 color-coded components flowing left to right:
1. INGESTION (blue): Transaction Simulator → 5 fraud types, 1 TPS stream
2. SCORING (purple): Feature Engine (17 features) → ML Model (GradientBoosting) → risk score
3. CASES (red): Auto-Case Creator → AI Explainer (Llama 3.1 local)
4. LEARNING (green): Analyst labels → Retrain model → Metrics improve (F1: 0.57→0.97)
5. PATTERNS (amber, below main flow): Graph Mining → Rings, Hubs, Velocity Spikes, Clusters

Key visual: Bold green feedback arrow from "Retrain" back to "ML Model" — the self-improving loop.

Database cylinder (gray) below, connected to all layers.
Tech stack bar at bottom: Python, FastAPI, Streamlit, scikit-learn, NetworkX, Ollama, SQLite.

Clean rounded rectangles, subtle shadows, white text on colored boxes, labeled arrows, professional font.
```

---

## Style Reference Notes for Nanobanaa

- **ByteByteGo style** = Alex Xu's system design diagrams: clean, colorful blocks, orthogonal arrows, no hand-drawn aesthetics
- The feedback loop (green arrow from Layer 4 back to Layer 2) is THE most important visual — it's what makes the system autonomous and self-improving
- Keep text minimal inside boxes — just the component name and a one-line description
- The diagram should be readable from 10 feet away on a projector
- Prefer landscape 16:9 for screen sharing during demo
