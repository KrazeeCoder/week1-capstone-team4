# week1-capstone-team4

Shazam-style audio fingerprinting, plus an evaluation harness for a
retrieval-vs-ranking diagnosis and a topological reranker for
pitch-shifted clips.

## Setup

```
pip install -r requirements.txt
```

## Evaluating retrieval and reranking

```
python build_eval_database.py          # builds eval_data.pkl from local WAVs
python evaluate_retrieval.py            # clean-clip baseline: recall@1/5/10
python evaluate_robustness.py --mode pitch   # pitch-shift degradation sweep
python evaluate_rerank.py --gate-ratio 1.5   # Stage 1 vs. gated topological rerank
```

## Team demo

```
python run_demo.py
```

Opens a Streamlit app with the headline findings chart and a live query tab
(pick a song, pitch-shift it, watch Stage 1's ranked list vs. the reranked
list side by side). `run_demo.py` wraps `streamlit run streamlit_demo.py`
with a workaround for a Windows-only ssl/tornado import crash -- run that
script rather than `streamlit run` directly.
