# westquant-core

Framework-neutral substrate for WestQuant Open representation search.

## Alpha contents

- WQIR-style typed representations across problem, Hamiltonian/operator,
  circuit/program, layout, control, hardware, execution, evaluation and
  resource-estimation layers;
- RepGraph v0.2 DAG with explicit transformation provenance;
- Transformation Registry;
- framework-neutral plugin protocols;
- deterministic beam search with explicit state/action rollouts;
- Pareto utilities;
- dataset manifests and JSONL utilities;
- canonical `wqt-policy-v0.1` training-record schema and lightweight validator.

WQT20 is intentionally not a runtime dependency. Deterministic and heuristic
search remain fully usable without a learned model, giving a clean baseline for
future WQT20 comparisons.
