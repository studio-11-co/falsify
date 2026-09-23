"""Run the acceptance tests fixed by plan AP-2026-001 (criteria-C1 and criteria-C2).

Illustrative example: Falsify OU plays both supplier and client. Writes result.json.
The criteria records were committed to the public registry before this script ran;
that ordering is the producer's statement, supported by the linkage start records.
"""
import json, numpy as np, yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

m = yaml.safe_load(open("criteria-C1.prml.yaml"))
SEED = m["seed"]

rows = [l.split() for l in open("german.data") if l.strip()]
X_raw = [r[:20] for r in rows]
y = np.array([1 if r[20] == "1" else 0 for r in rows])           # 1 = good credit
cat = [i for i in range(20) if X_raw[0][i].startswith("A")]
num = [i for i in range(20) if i not in cat]
X = np.array(X_raw, dtype=object)
sex = np.array(["female" if r[8] == "A92" else "male" for r in rows])

Xtr, Xte, ytr, yte, _, sxte = train_test_split(
    X, y, sex, test_size=0.30, random_state=SEED, stratify=y)      # stratified 70/30

pipe = Pipeline([
    ("prep", ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ("num", StandardScaler(), num)])),
    ("clf", LogisticRegression(penalty="l2", C=1.0, max_iter=2000, random_state=SEED)),
])
pipe.fit(Xtr.tolist(), ytr)
pred = pipe.predict(Xte.tolist())

sel_f = float(pred[sxte == "female"].mean())
sel_m = float(pred[sxte == "male"].mean())
result = {
    "plan_id": "AP-2026-001",
    "C1_impact_ratio": round(sel_f / sel_m, 6),
    "C2_accuracy": round(float((pred == yte).mean()), 6),
    "selection_female": round(sel_f, 6),
    "selection_male": round(sel_m, 6),
    "n_test": int(len(yte)),
}
json.dump(result, open("result.json", "w"), indent=2, sort_keys=True)
print(json.dumps(result, indent=2, sort_keys=True))
