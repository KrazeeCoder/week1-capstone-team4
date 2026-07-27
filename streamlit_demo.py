"""Team demo: retrieval-vs-ranking failure diagnosis + topological reranking.

Run with:
    streamlit run streamlit_demo.py

Two sections:
  1. Findings -- the headline sweep results from evaluate_robustness.py /
     evaluate_rerank.py, baked in as constants (re-running the full sweep
     live takes ~20 min and is CQT/CPU heavy -- see README note in the app).
  2. Live demo -- pick a song from the eval DB, optionally pitch-shift a
     random clip, and watch Stage-1's ranked list vs. the gated topological
     reranker's list side by side, with the true song highlighted.
"""
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
import streamlit as st

from database import AudioDatabase
from load_audio import load_audio, standardize_rate
from random_clips import make_random_clip
from eval_utils import query_clip, rank_of, LRUAudioCache
from topological_rerank import rerank_candidates

TARGET_RATE = 44100

# Colorblind-safe categorical palette (Okabe-Ito), fixed assignment per series.
COLOR_STAGE1 = "#0072B2"       # blue
COLOR_RERANK_GATED = "#D55E00"  # vermillion
COLOR_RERANK_UNGATED = "#999999"  # neutral gray -- de-emphasized, superseded approach

# Headline results from the 20-song x 6-shift sweep (evaluate_rerank.py),
# clip_length=10s, top_n=3. See eval_rerank_full.log / eval_rerank_gated.log.
PITCH_SHIFTS = [-4, -2, -1, 0, 1, 2, 4]
RECALL_STAGE1 = [0.10, 0.20, 0.10, 1.00, 0.20, 0.15, 0.20]
RECALL_RERANK_UNGATED = [0.10, 0.20, 0.15, 1.00, 0.25, 0.05, 0.25]
RECALL_RERANK_GATED = [0.05, 0.20, 0.15, 1.00, 0.30, 0.10, 0.30]

st.set_page_config(page_title="Song ID: retrieval vs. ranking", layout="wide")
st.title("Song retrieval + topological reranking")
st.caption(
    "Diagnosing why short/pitch-shifted clips fail Shazam-style fingerprinting, "
    "and whether a topological reranker recovers the failures."
)

tab_findings, tab_demo = st.tabs(["Findings", "Live demo"])

# ---------------------------------------------------------------- Findings --
with tab_findings:
    st.subheader("Pitch shift breaks ranking, not retrieval")
    st.markdown(
        "On clean, unmodified clips Stage 1 (hash-tally voting) gets **97-100% recall@1**. "
        "Pitch-shift a clip by even 1-2 semitones and recall@1 collapses to **10-25%** -- "
        "but the correct song is *still retrieved* (0% retrieval_failure across every shift "
        "tested). It's ranked wrong, not missing."
    )

    col1, col2 = st.columns([3, 2])
    with col1:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(PITCH_SHIFTS, RECALL_STAGE1, marker="o", linewidth=2, color=COLOR_STAGE1, label="Stage 1 only")
        ax.plot(
            PITCH_SHIFTS, RECALL_RERANK_UNGATED, marker="o", linewidth=2,
            color=COLOR_RERANK_UNGATED, linestyle="--", label="+ rerank (ungated)",
        )
        ax.plot(
            PITCH_SHIFTS, RECALL_RERANK_GATED, marker="o", linewidth=2,
            color=COLOR_RERANK_GATED, label="+ rerank (confidence-gated)",
        )
        ax.set_xlabel("Pitch shift (semitones)")
        ax.set_ylabel("Recall@1")
        ax.set_ylim(0, 1.05)
        ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0%}")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(frameon=False)
        ax.set_title("Recall@1 vs. pitch shift (20 songs, 10s clips)")
        st.pyplot(fig)

    with col2:
        st.metric("Clean-clip recall@1 (baseline)", "97-100%")
        st.metric(
            "Avg recall@1 under pitch shift, Stage 1 only",
            f"{np.mean([r for s, r in zip(PITCH_SHIFTS, RECALL_STAGE1) if s != 0]):.1%}",
        )
        st.metric(
            "Avg recall@1, gated rerank",
            f"{np.mean([r for s, r in zip(PITCH_SHIFTS, RECALL_RERANK_GATED) if s != 0]):.1%}",
            delta=f"{np.mean([r for s, r in zip(PITCH_SHIFTS, RECALL_RERANK_GATED) if s != 0]) - np.mean([r for s, r in zip(PITCH_SHIFTS, RECALL_STAGE1) if s != 0]):+.1%}",
        )
        st.markdown(
            "**Why gating matters:** the ungated reranker demoted almost as many "
            "already-correct Stage-1 picks as it fixed (net lift ~+1pp). Only "
            "reranking when Stage 1's top score doesn't already dominate the "
            "runner-up roughly **tripled** the net lift."
        )

    st.info(
        "Numbers above are from a fixed sweep (`evaluate_rerank.py`, 20 songs x 6 pitch "
        "shifts x 10s clips) -- re-run it yourself to reproduce or extend.",
        icon="ℹ️",
    )

# --------------------------------------------------------------- Live demo --
with tab_demo:
    db_path = st.sidebar.text_input("Database file", value="eval_data.pkl")
    top_n = st.sidebar.slider("Rerank top-N", 1, 10, 3)
    gate_ratio = st.sidebar.slider("Rerank confidence gate ratio", 1.0, 3.0, 1.5, 0.1)

    @st.cache_resource
    def get_db(path):
        db = AudioDatabase(path)
        db.load_data()
        return db

    @st.cache_resource
    def get_audio_cache():
        return LRUAudioCache(load_audio, capacity=6)

    db = get_db(db_path)
    if not db.metadata:
        st.error(f"No songs found in {db_path}. Run build_eval_database.py first.")
        st.stop()

    audio_cache = get_audio_cache()
    titles = {song_id: f"{info['title']} -- {info['artist']}" for song_id, info in db.metadata.items()}

    def render_ranked(container, title, ranked_list, highlight_id=None, true_rank=None):
        with container:
            st.markdown(f"**{title}**")
            if not ranked_list:
                st.warning("No candidates retrieved.")
                return
            for idx, (sid, score) in enumerate(ranked_list[:top_n]):
                label = titles.get(sid, f"song {sid}")
                row = f"{idx + 1}. {label}  (score={score})"
                if highlight_id is not None and sid == highlight_id:
                    st.success(row)
                else:
                    st.text(row)
            if highlight_id is not None:
                if true_rank is None:
                    st.caption("True song never shared a fingerprint hash with this clip.")
                elif true_rank > top_n:
                    st.caption(f"True song retrieved at rank {true_rank} (outside top-{top_n}).")

    def run_identification(clip, rate, true_song_id=None):
        with st.spinner("Stage 1: fingerprint + query..."):
            stage1_result = query_clip(clip, rate, db, k=max(10, top_n))
        with st.spinner("Stage 2: topological rerank..."):
            reranked = rerank_candidates(
                clip, rate, db, stage1_result, top_n=top_n, audio_cache=audio_cache, gate_ratio=gate_ratio,
            )

        col1, col2 = st.columns(2)
        stage1_rank = rank_of(stage1_result, true_song_id) if true_song_id is not None else None
        rerank_rank = None
        if true_song_id is not None:
            rerank_rank = next((i + 1 for i, (sid, _s) in enumerate(reranked) if sid == true_song_id), None)

        render_ranked(col1, "Stage 1 (hash-tally)", stage1_result["ranked"], true_song_id, stage1_rank)
        render_ranked(col2, f"+ Topological rerank (top-{top_n})", reranked, true_song_id, rerank_rank)

        if true_song_id is not None:
            m1, m2 = st.columns(2)
            m1.metric("Stage 1 rank", stage1_rank if stage1_rank else "not retrieved")
            m2.metric(
                "Rerank rank", rerank_rank if rerank_rank else "not retrieved",
                delta=(None if stage1_rank is None or rerank_rank is None else rerank_rank - stage1_rank),
                delta_color="inverse",
            )
        elif stage1_result["ranked"]:
            best_id, best_score = stage1_result["ranked"][0]
            st.info(f"Best guess: **{titles.get(best_id, best_id)}** (Stage 1 score {best_score})")

    mode = st.radio(
        "Query source",
        ["Record from microphone (real test)", "Known clip from database (controlled test)"],
    )

    # ---------------------------------------------------------- Mic mode --
    if mode == "Record from microphone (real test)":
        st.caption(
            "Uses your browser's microphone (Streamlit's st.audio_input) -- not a "
            "simulated clip. Play a song near your mic and record a few seconds."
        )
        audio_value = st.audio_input("Record a clip of a song playing")

        if audio_value is not None:
            st.audio(audio_value)
            if st.button("Identify", type="primary"):
                with st.spinner("Decoding recording..."):
                    data, sr = sf.read(audio_value)
                    if data.ndim == 2:
                        data = data.mean(axis=1)
                    clip, rate = standardize_rate(data, sr, TARGET_RATE)
                    clip = clip.astype(np.float32)
                run_identification(clip, rate, true_song_id=None)
        else:
            st.info("Click the microphone icon above to record.", icon="🎙️")

    # ------------------------------------------------------- Database mode --
    else:
        st.caption(
            "Cuts a clip from a song already in the database (known answer), optionally "
            "pitch-shifted -- useful for reproducing the Findings chart on a single example."
        )
        song_id = st.selectbox("Song", options=list(titles), format_func=lambda sid: titles[sid])

        col_a, col_b, col_c = st.columns(3)
        clip_length = col_a.slider("Clip length (s)", 3, 20, 10)
        pitch_shift = col_b.slider("Pitch shift (semitones)", -6, 6, 0)
        seed = col_c.number_input("Random seed", value=0, step=1)

        if st.button("Identify", type="primary"):
            with st.spinner("Loading audio..."):
                try:
                    samples, rate = audio_cache.get_or_load(song_id, db.metadata[song_id]["filename"])
                except FileNotFoundError:
                    st.error(f"Audio file not found: {db.metadata[song_id]['filename']}")
                    st.stop()

            rng = np.random.default_rng(int(seed))
            clip = make_random_clip(samples, clip_length, rate, rng).astype(np.float32)

            if pitch_shift != 0:
                import librosa
                with st.spinner(f"Applying {pitch_shift:+d} semitone pitch shift..."):
                    clip = librosa.effects.pitch_shift(y=clip, sr=rate, n_steps=pitch_shift)

            run_identification(clip, rate, true_song_id=song_id)
