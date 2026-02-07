# Text Data vs General LLM Embedding Feature Engineering: Comparative Analysis

**Date:** 2026-02-05
**Purpose:** Assess applicability to fraud detection autonomous agent

---

## Article Overview

### Article 1: "7 Advanced Feature Engineering Tricks Using LLM Embeddings"
- **Author:** Shittu Olumide
- **Published:** February 4, 2026
- **Focus:** General-purpose embedding feature engineering (broader applicability)

### Article 2: "7 Advanced Feature Engineering Tricks for Text Data Using LLM Embeddings"
- **Author:** Iván Palomares Carrascosa
- **Published:** October 30, 2025
- **Focus:** Text-specific data engineering with embeddings

---

## Key Differences Between Articles

### 1. Scope and Philosophy

**General Article (Tricks Using LLM Embeddings):**
- Broader, more strategic approach
- Focuses on transformation and optimization of embeddings themselves
- Emphasizes interpretability and explainability
- More about "what to do with embeddings once you have them"

**Text Data Article (Tricks for Text Data):**
- More tactical and domain-specific
- Focuses on combining embeddings with traditional text features
- Emphasizes hybrid approaches (semantic + lexical)
- More about "enriching text pipelines with embeddings"

### 2. Technique Overlap

| Technique | General Article | Text Data Article | Notes |
|-----------|----------------|-------------------|-------|
| Semantic similarity to anchors | ✓ (#1) | ✓ (#3) | Near-identical technique |
| Dimensionality reduction | ✓ (#2 - PCA/SVD) | ✓ (#5 - PCA + Poly) | Text version adds polynomial expansion |
| Clustering features | ✓ (#3 - KMeans) | ✓ (#2 - KMeans) | Near-identical technique |
| Pairwise/contrastive features | ✓ (#4 - differences) | ✓ (#6 - differences) | Near-identical technique |
| Whitening normalization | ✓ (#5) | ✗ | General article only |
| Word-level aggregation | ✓ (#6) | ✗ | General article only |
| AutoML synthesis | ✓ (#7) | ✗ | General article only |
| TF-IDF fusion | ✗ | ✓ (#1) | Text article only |
| Meta-feature stacking | ✗ | ✓ (#4) | Text article only |
| Cross-modal fusion | ✗ | ✓ (#7) | Text article only |

---

## Unique Techniques in Text Data Article

### 1. TF-IDF + Embedding Fusion (#1)
**What it does:**
- Combines traditional TF-IDF lexical features with semantic embeddings
- Captures both keyword importance and semantic meaning
- Tested on 20newsgroups dataset

**Code pattern:**
```python
tfidf = TfidfVectorizer(max_features=300).fit_transform(texts).toarray()
emb = model.encode(texts)
X = np.hstack([tfidf, StandardScaler().fit_transform(emb)])
```

**Why it matters:**
- Hybrid approach: lexical precision + semantic context
- Proven to boost accuracy on text classification

### 2. Meta-Feature Stacking via Auxiliary Classifier (#4)
**What it does:**
- Train auxiliary classifier on embeddings
- Use prediction probabilities as new meta-features
- Stack meta-features with original embeddings

**Code pattern:**
```python
meta_clf = LogisticRegression().fit(X_train, y_train)
meta_feature = meta_clf.predict_proba(emb)[:, 1].reshape(-1, 1)
X_aug = np.hstack([emb_scaled, meta_feature])
```

**Why it matters:**
- Creates discriminative features from model reasoning
- Similar to stacking in ensemble methods

### 3. Cross-Modal Fusion (#7)
**What it does:**
- Combines embeddings with handcrafted linguistic features
- Examples: punctuation ratio, word count, special character density

**Code pattern:**
```python
lengths = np.array([len(t.split()) for t in texts]).reshape(-1, 1)
punct_ratio = np.array([len(re.findall(r"[^\w\s]", t)) / len(t) for t in texts]).reshape(-1, 1)
X = np.hstack([emb, lengths, punct_ratio])
```

**Why it matters:**
- Unites semantic with statistical/syntactic signals
- Captures surface-level patterns embeddings might miss

---

## Unique Techniques in General Article

### 1. Embedding Whitening Normalization (#5)
**What it does:**
- Rescales embeddings to zero mean and unit covariance
- Equalizes importance across dimensions
- Used in state-of-the-art semantic search

**Code pattern:**
```python
scaler = StandardScaler(with_std=False)
embeddings_centered = scaler.fit_transform(embeddings)
pca = PCA(whiten=True)
embeddings_whitened = pca.fit_transform(embeddings_centered)
```

**Why it matters:**
- Prevents high-variance directions from dominating
- Standard in Sentence-BERT pipelines
- Critical for fair similarity comparisons

### 2. Word-Level vs Sentence-Level Aggregation (#6)
**What it does:**
- Uses token embeddings from BERT/transformers
- Applies strategic pooling: mean, max, or CLS token
- Captures fine-grained information in long documents

**Code pattern:**
```python
outputs = model(**inputs)
token_embeddings = outputs.last_hidden_state
# Mean pooling with attention mask
masked = token_embeddings * attention_mask
summed = masked.sum(dim=1)
```

**Why it matters:**
- Single document embedding loses nuance
- Mean pooling averages noise, max pooling highlights salience
- Better for multi-topic or long documents

### 3. AutoML Feature Synthesis (#7)
**What it does:**
- Uses PolynomialFeatures on reduced embeddings
- Automatically discovers non-linear interactions
- Creates second-degree polynomial features

**Code pattern:**
```python
embeddings_reduced = PCA(n_components=20).fit_transform(embeddings)
poly = PolynomialFeatures(degree=2, interaction_only=False)
synthesized_features = poly.fit_transform(embeddings_reduced)
```

**Why it matters:**
- Manual interaction engineering impractical at 384+ dimensions
- Captures complex semantic relationships
- Requires strong regularization to avoid overfitting

---

## Fraud Detection Applicability Assessment

### High-Value Text Data Techniques for Fraud

#### 1. TF-IDF + Embedding Fusion (Text #1)
**Fraud Use Case:**
- Transaction descriptions (e.g., "ATM withdrawal", "online purchase")
- Case summaries generated by LLM
- Pattern card descriptions

**Why applicable:**
- Fraud has keyword signals: "ATM", "casino", "wire transfer"
- Embeddings capture semantic: "cash advance" ≈ "ATM withdrawal"
- Combined approach catches both exact matches and semantic variants

**Implementation for fraud agent:**
```python
# Transaction descriptions
descriptions = ["ATM withdrawal downtown", "Online casino deposit", "Wire transfer international"]
tfidf = TfidfVectorizer(max_features=100).fit_transform(descriptions).toarray()
emb = model.encode(descriptions)
fraud_features = np.hstack([tfidf, StandardScaler().fit_transform(emb)])
```

#### 2. Meta-Feature Stacking (Text #4)
**Fraud Use Case:**
- Analyst labels as training signal
- LLM risk assessments as meta-features
- Stacking multiple risk scores

**Why applicable:**
- Autonomous agent generates explanations → embeddings
- Auxiliary model predicts "fraud probability"
- Stack that probability with transaction features

**Implementation for fraud agent:**
```python
# Train auxiliary classifier on labeled cases
case_summaries_emb = model.encode(case_summaries)
aux_clf = LogisticRegression().fit(case_summaries_emb, analyst_labels)

# Use predictions as meta-features
fraud_prob = aux_clf.predict_proba(new_case_emb)[:, 1].reshape(-1, 1)
augmented_features = np.hstack([transaction_features, fraud_prob])
```

#### 3. Cross-Modal Fusion (Text #7)
**Fraud Use Case:**
- Combine LLM explanations with transaction metadata
- Transaction amount, velocity, merchant category codes
- Merge semantic reasoning with numerical signals

**Why applicable:**
- Fraud is inherently multi-modal: text + numbers + graph
- Pattern cards have text descriptions + numerical metrics
- LLM summaries can be enriched with statistical features

**Implementation for fraud agent:**
```python
# Pattern card descriptions with numerical metadata
pattern_embeddings = model.encode(pattern_descriptions)
num_features = np.array([
    [transaction_count, avg_amount, time_span],
    [transaction_count2, avg_amount2, time_span2]
])
hybrid_pattern_features = np.hstack([pattern_embeddings, num_features])
```

#### 4. Semantic Anchor Similarity (Both articles)
**Fraud Use Case:**
- Define fraud typology anchors: "account takeover", "money laundering", "card testing"
- Measure similarity of transactions/patterns to known fraud types
- Generate interpretable fraud-type-specific features

**Why applicable:**
- Fraud has known typologies (enumerated in `/sim/typologies`)
- Similarity to typology embeddings = soft classification
- Interpretable for analyst review

**Implementation for fraud agent:**
```python
fraud_anchors = [
    "account takeover credential stuffing",
    "money laundering structuring",
    "card testing micro-transactions",
    "merchant collusion refund abuse"
]
anchor_emb = model.encode(fraud_anchors)

# For each transaction description or case summary
case_emb = model.encode(case_summaries)
typology_scores = cosine_similarity(case_emb, anchor_emb)
# typology_scores[i] = [ATO_score, ML_score, card_testing_score, collusion_score]
```

#### 5. Cluster-Based Topic Discovery (Both articles)
**Fraud Use Case:**
- Unsupervised discovery of emerging fraud patterns
- Cluster transaction descriptions or case narratives
- Pattern cards as cluster representatives

**Why applicable:**
- Fraud patterns evolve (concept drift)
- Clustering finds unknown fraud modes
- Distance to cluster centroids = anomaly score

**Implementation for fraud agent:**
```python
# Pattern mining job embeddings
all_transaction_embeddings = model.encode(all_transaction_descriptions)
kmeans = KMeans(n_clusters=20, random_state=42)
cluster_labels = kmeans.fit_predict(all_transaction_embeddings)
distances = kmeans.transform(all_transaction_embeddings)

# New features: cluster assignment + distance to centroids
# High distance to all clusters = anomaly/new pattern
min_distance = distances.min(axis=1)  # Anomaly score
```

---

## Creative Fraud-Specific Applications

### 1. LLM-Generated Case Summaries as Embedding Source
**Concept:**
The autonomous agent generates natural language case summaries like:
```
"High-risk transaction: $9,950 wire transfer to offshore account.
Customer has no prior international activity. Follows pattern of 3 similar
transactions in 48 hours. Possible structuring to evade $10k reporting threshold."
```

**Feature engineering:**
- Embed these summaries with sentence-transformers
- Apply semantic similarity to fraud typology anchors
- Use as input to downstream fraud prediction model

**Why powerful:**
- LLM reasoning captured as dense vector
- Explainability preserved (original text)
- Bridges symbolic reasoning (LLM) and statistical models (sklearn)

### 2. Pattern Card Description Embeddings
**Concept:**
Pattern cards have natural language descriptions:
```
"Rapid-fire small transactions pattern: 15+ transactions under $50
within 1 hour from same account. Often seen in card testing attacks
where fraudster validates stolen card numbers."
```

**Feature engineering:**
- Embed pattern descriptions
- Cluster similar patterns
- Measure new transaction similarity to known pattern embeddings
- Pattern matching becomes semantic search problem

**Why powerful:**
- Pattern library becomes searchable embedding space
- New transactions retrieve similar historical patterns
- "Memory" system for fraud agent

### 3. Merchant Description Semantic Features
**Concept:**
Transaction descriptions often contain merchant info:
```
"AMZN MKTP US", "PAYPAL *ONLINECASINO", "VENMO PAYMENT"
```

**Feature engineering:**
- Embed merchant descriptions
- Calculate similarity to high-risk merchant anchors
- Create "merchant category semantic" features

**Why powerful:**
- Fraud-prone merchants cluster semantically
- "casino", "gaming", "crypto" semantically similar
- Catches obfuscated merchant names

### 4. Temporal Narrative Embeddings
**Concept:**
Create narrative of account activity over time:
```
"Normal retail purchases for 6 months. Sudden switch to high-value
international wire transfers. Account credentials likely compromised."
```

**Feature engineering:**
- Generate temporal narrative with LLM
- Embed narrative
- Use as "behavioral shift" feature

**Why powerful:**
- Captures longitudinal behavioral changes
- Fraud often involves pattern breaks
- Temporal context encoded semantically

### 5. Analyst Feedback Loop via Meta-Features
**Concept:**
- Train auxiliary model on analyst-labeled cases
- Model learns "what analysts consider suspicious"
- Use auxiliary model predictions as meta-features

**Feature engineering:**
```python
# Analyst feedback training
analyst_labeled_cases = get_labeled_cases()
case_embeddings = model.encode([c.summary for c in analyst_labeled_cases])
analyst_model = LogisticRegression().fit(case_embeddings, [c.label for c in analyst_labeled_cases])

# Meta-feature for new cases
new_case_emb = model.encode(new_case.summary)
analyst_suspicion_score = analyst_model.predict_proba(new_case_emb)[:, 1]
```

**Why powerful:**
- Captures implicit analyst knowledge
- Self-improving via feedback loop
- Meta-feature = "how suspicious would analyst find this?"

---

## Performance Benchmarks

### From Text Data Article
- **No explicit benchmarks provided**
- Uses 20newsgroups dataset for demo
- Reports "often boosting accuracy" (qualitative)

### From General Article
- **No explicit benchmarks provided**
- Emphasizes validation and careful testing
- Notes PCA can retain 100% variance with small datasets
- Warnings about overfitting with polynomial features

### Benchmark Gap
Neither article provides rigorous quantitative comparisons:
- No accuracy improvements quantified
- No fraud-specific datasets tested
- No ablation studies

**Implication for our project:**
- Must benchmark ourselves on fraud data
- Create validation harness in `/tests`
- Track metric improvements per technique

---

## Recommended Implementation Priority for Fraud Agent

### Phase 1: High-Impact, Low-Risk (MVP)
1. **Semantic Anchor Similarity** (Both articles #1/#3)
   - Define 5-10 fraud typology anchors
   - Compute similarity features
   - Interpretable, fast, proven

2. **Cross-Modal Fusion** (Text #7)
   - Combine LLM case summaries with transaction amounts, velocity
   - Already have numerical features in `/risk`
   - Natural extension of existing pipeline

### Phase 2: Learning Improvements (Post-MVP)
3. **Clustering for Pattern Discovery** (Both articles #2/#3)
   - Mine transaction embeddings for emerging patterns
   - Integrate with `/patterns` graph mining
   - Fits "self-improving" narrative

4. **Meta-Feature Stacking** (Text #4)
   - Train auxiliary model on analyst labels
   - Use predictions as features
   - Demonstrates learning from feedback

### Phase 3: Advanced Optimizations (If Time)
5. **Whitening Normalization** (General #5)
   - Improve similarity calculations
   - Better pattern matching accuracy
   - State-of-the-art technique

6. **TF-IDF Fusion** (Text #1)
   - Hybrid lexical + semantic for transaction descriptions
   - Catch exact keyword matches + variants
   - Proven boost on text classification

### Deprioritized (Not Critical for Demo)
- Word-level aggregation (complex, marginal benefit)
- AutoML polynomial synthesis (overfitting risk, hard to explain)

---

## Code Integration Strategy

### 1. Create Embedding Feature Module
**New file:** `/risk/embedding_features.py`

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class FraudEmbeddingFeatures:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

        # Define fraud typology anchors
        self.fraud_anchors = [
            "account takeover credential stuffing",
            "money laundering cash structuring",
            "card testing small transactions",
            "refund abuse merchant collusion"
        ]
        self.anchor_embeddings = self.model.encode(self.fraud_anchors)

    def semantic_typology_features(self, text: str) -> np.ndarray:
        """Compute similarity to fraud typology anchors."""
        emb = self.model.encode([text])
        similarities = cosine_similarity(emb, self.anchor_embeddings)
        return similarities.flatten()

    def cross_modal_features(self, text: str, numerical_features: np.ndarray) -> np.ndarray:
        """Combine text embeddings with numerical features."""
        text_emb = self.model.encode([text])
        return np.hstack([text_emb, numerical_features.reshape(1, -1)])
```

### 2. Integrate with Existing Pipeline
**Modify:** `/backend/orchestrator.py`

```python
from risk.embedding_features import FraudEmbeddingFeatures

class Orchestrator:
    def __init__(self):
        # ... existing init ...
        self.embedding_features = FraudEmbeddingFeatures()

    async def process_transaction(self, txn: Transaction):
        # ... existing risk scoring ...

        # Generate LLM case summary
        case_summary = self.generate_case_summary(txn, risk_result)

        # Add semantic typology features
        typology_scores = self.embedding_features.semantic_typology_features(case_summary)
        risk_result.typology_scores = typology_scores.tolist()

        # ... continue with case creation ...
```

### 3. Update Schema
**Modify:** `/schemas/risk_result.schema.json`

```json
{
  "properties": {
    "typology_scores": {
      "type": "array",
      "items": {"type": "number"},
      "description": "Semantic similarity to fraud typology anchors"
    }
  }
}
```

### 4. Visualize in UI
**Modify:** `/ui/app.py`

```python
# Pattern matching visualization
st.subheader("Fraud Typology Scores")
typology_labels = ["Account Takeover", "Money Laundering", "Card Testing", "Refund Abuse"]
scores = case.risk_result.typology_scores

fig = px.bar(x=typology_labels, y=scores, title="Semantic Similarity to Known Fraud Types")
st.plotly_chart(fig)
```

---

## Fraud-Specific vs General Text Considerations

### Why Fraud is Different from General Text

1. **Short, structured text:**
   - Transactions: "ATM WD 123 MAIN ST $200"
   - Not long documents (no need for word-level pooling)

2. **Domain-specific vocabulary:**
   - "Structuring", "mule", "ATO", "BIN"
   - May need domain-tuned embeddings (future work)

3. **Numerical signals dominate:**
   - Amount, velocity, time critical
   - Text is supplementary (but growing with LLM reasoning)

4. **Interpretability critical:**
   - Analysts need explanations
   - Semantic anchor similarity > black-box embeddings

5. **Adversarial actors:**
   - Fraudsters obfuscate
   - Semantic similarity catches paraphrasing
   - "casino" → "gaming establishment" → "entertainment venue"

---

## Recommendations Summary

### DO:
1. Implement semantic anchor similarity for typology classification
2. Use cross-modal fusion for LLM summaries + numerical features
3. Apply clustering for unsupervised pattern discovery
4. Leverage meta-feature stacking with analyst feedback loop
5. Benchmark each technique on fraud data before production use

### DON'T:
1. Over-engineer with polynomial features (overfitting risk)
2. Use word-level pooling (transactions too short)
3. Apply without dimensionality checks (curse of dimensionality)
4. Skip validation (embeddings can introduce noise)
5. Ignore interpretability (explain why embedding features matter)

### MEASURE:
1. Precision/recall before and after embedding features
2. False positive rate impact
3. Analyst review time (does it help prioritization?)
4. Pattern discovery rate (new fraud modes found)
5. Computational overhead (embeddings add latency)

---

## Memory Bank Update

```
[2026-02-05] Text vs General Embeddings Analysis
→ Text article emphasizes hybrid (TF-IDF + embeddings), meta-features, cross-modal fusion
→ General article emphasizes whitening, word-level pooling, AutoML synthesis
→ For fraud: prioritize semantic anchors, cross-modal fusion, clustering
→ Fraud has short structured text + numerical dominance → different from NLP benchmarks
→ Actionable: Create `/risk/embedding_features.py` with typology similarity + cross-modal fusion
→ Demo value: Show pattern cards as semantic clusters with typology labels
```

---

## Next Steps

1. Create `/risk/embedding_features.py` module
2. Define fraud typology anchor texts (consult `/sim/typologies`)
3. Integrate semantic features into risk scoring pipeline
4. Update schemas for typology_scores field
5. Add UI visualization for typology similarity
6. Benchmark: fraud detection accuracy with/without embeddings
7. Document in `/docs/EMBEDDING_FEATURES.md`

---

**Conclusion:**

The text data article provides 3 unique techniques highly applicable to fraud:
1. TF-IDF fusion (lexical + semantic)
2. Meta-feature stacking (model reasoning as features)
3. Cross-modal fusion (text + numbers)

Combined with general article's semantic anchors and clustering, we have a powerful toolkit for:
- Typology classification (interpretable)
- Pattern discovery (unsupervised)
- LLM reasoning integration (cross-modal)
- Analyst feedback learning (meta-features)

Priority: **Semantic anchors + Cross-modal fusion** for MVP demo clarity.
