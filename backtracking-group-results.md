# Platform revisitation analysis

A return means landing on a platform whose ID was previously observed in the same session.

## Experience-group bootstrap

| Metric | Estimate (1–2 minus 3–4) | 95% interval |
|---|---:|---:|
| Return landings / platform landings | -0.051 | [-0.112, 0.007] |
| Revisited platforms / unique platforms | -0.015 | [-0.072, 0.040] |
| Return episodes / platform landings | -0.008 | [-0.023, 0.009] |

## Scenario × experience interactions

P-values are exploratory Wald tests; Holm correction is within the B/C/D family for each metric and model.

| Metric | Model | B p | B Holm p | C p | C Holm p | D p | D Holm p |
|---|---|---:|---:|---:|---:|---:|---:|
| Return landings / platform landings | LMM | 0.699 | 1 | 0.5468 | 1 | 0.239 | 0.7171 |
| Return landings / platform landings | GEE | 0.5757 | 1 | 0.5521 | 1 | 0.03157 | 0.0947 |
| Revisited platforms / unique platforms | LMM | 0.5755 | 1 | 0.6458 | 1 | 0.1979 | 0.5936 |
| Revisited platforms / unique platforms | GEE | 0.4158 | 0.8316 | 0.6508 | 0.8316 | 0.1046 | 0.3138 |
| Return episodes / platform landings | LMM | 0.824 | 0.8865 | 0.4433 | 0.8865 | 0.02592 | 0.07776 |
| Return episodes / platform landings | GEE | 0.7764 | 1 | 0.5059 | 1 | 0.03538 | 0.1061 |

## High/low audio condition × experience

| Metric | Model | Coefficient | p-value |
|---|---|---:|---:|
| Return landings / platform landings | LMM | -0.081 | 0.1416 |
| Return landings / platform landings | GEE | -0.081 | 0.1503 |
| Revisited platforms / unique platforms | LMM | -0.070 | 0.1085 |
| Revisited platforms / unique platforms | GEE | -0.070 | 0.1584 |
| Return episodes / platform landings | LMM | -0.027 | 0.08217 |
| Return episodes / platform landings | GEE | -0.027 | 0.1988 |
