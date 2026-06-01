# FYP Jury Evaluation Guide — Q&A Session

**Project:** Linux Keylogger Detection via Behavioral Analysis + ML  
**Prepared for:** External FYP evaluators, thesis defense jury, and project supervisors  
**Last updated:** June 2026

This document simulates a **detailed examiner Q&A**. Each question reflects common jury concerns; answers cite project evidence and suggest **what to demonstrate live**.

---

## Part 1 — Motivation & Problem Statement

### Q1. Why do we need another keylogger detector? Aren't antivirus products enough?

**Answer:** Commercial antivirus relies primarily on **signatures** and **static file analysis**. Custom, in-house, or polymorphic keyloggers — especially on Linux — often evade these tools. Public datasets show that many keyloggers are delivered as **short Python scripts** or **userspace `/dev/input` readers** with no known hash.

This project targets **behavioral indicators** visible at the kernel and syscall layer:

- Who is reading the keyboard input stream?  
- How fast? From which process context?  
- What companion syscall patterns appear (mass read/open/connect)?

**Differentiator:** Detection runs **continuously** and **without prior knowledge** of the malware binary.

**Demo pointer:** Run an **unseen** script from `dataset/.../unseen keyloggers/` that is not in any training signature list.

---

### Q2. What real-world problem does this solve?

**Answer:** Keyloggers remain a top credential-theft mechanism (banking, VPN, email, SSH passphrases). On shared or research Linux workstations:

- Users may run untrusted Python tooling  
- Compromised pip packages can include input capture  
- Insider threats use off-the-shelf loggers  

The system gives a **local, privacy-preserving early warning** when input-stream access or telemetry deviates from normal desktop behavior.

**Limitation (honest):** This is an **academic prototype**, not a certified security product. It demonstrates feasibility rather than replacing enterprise EDR.

---

### Q3. Why Linux specifically?

**Answer:**

1. **Transparency** — kernel modules, eBPF, and `/dev/input` are well-documented for research  
2. **Gap in tooling** — Windows has more commercial anti-keylogger products; Linux desktop users often rely on generic ClamAV  
3. **FYP scope** — building a custom Netlink LKM demonstrates systems programming competence  

The ML dataset includes Windows L1 data for comparison but **training and live demo are Linux-only**.

---

## Part 2 — Novelty & Differentiation

### Q4. What is novel about this project?

**Answer:** Three contributions working together:

| Contribution | Novel aspect |
|--------------|--------------|
| **Privacy-preserving LKM** | Keyboard notifier captures **metadata only** (timing, PID, comm) — never keycodes |
| **Dual-path detection** | Real-time **heuristics** (Netlink) + **ML on eBPF telemetry** (syscall/process features) |
| **Tiered ML evaluation** | Refuses to claim perfect AUC from naive row splits; reports cross-level **Tier C** metrics |

Unlike a pure ML paper, this is a **working integrated system** (kernel → daemon → collector → API → GUI).

---

### Q5. How is this different from rkhunter, chkrootkit, or OSSEC?

**Answer:**

| Tool | Approach | Gap |
|------|----------|-----|
| rkhunter / chkrootkit | File integrity, known rootkit signatures | Miss userspace `/dev/input` loggers |
| OSSEC / HIDS | Log rules, FIM | No direct keyboard-stream visibility |
| **This project** | Kernel notifier + syscall telemetry ML | Targets **input capture behavior** specifically |

**Demo pointer:** Show daemon **Process** page when typing — benign apps whitelisted; unknown reader flagged.

---

### Q6. How is this different from using eBPF alone (Falco, Tracee)?

**Answer:** General eBPF security tools monitor **broad syscall policies**. This project:

1. Adds a **dedicated keyboard access path** (LKM) absent in generic tools  
2. Trains **level-specific models** (L2 hook vs L3 rootkit vs L4 kernel-adjacent) on curated datasets  
3. Presents a **unified GUI** for non-expert users with clear **Keylogger Detected / System Clean** states  

eBPF here is a **feature source for ML**, not the sole detector.

---

### Q7. Isn't capturing keyboard events still a privacy violation?

**Answer:** The design follows **data minimization**:

- **Not captured:** key values, scancodes, keycodes, clipboard  
- **Captured:** event timing, process identity, aggregate syscall rates  

See `docs/ETHICS.md` for formal analysis. The thesis framing: *detect access to the input channel, not content of input*.

**Jury follow-up:** "Could this be abused?" — With root, any monitor is powerful; scope is **local admin installs this for protection**, not covert surveillance.

---

## Part 3 — Architecture Questions

### Q8. Walk us through the architecture in 60 seconds.

**Answer:**

1. **Kernel module** hooks keyboard notifications → Netlink to userspace  
2. **Daemon** applies three heuristics → JSON status file  
3. **eBPF collector** samples syscall/process metrics every 0.5 s → CSV  
4. **ML API** scores each row with L2/L3/L4 ensembles + spike rules  
5. **GUI** polls daemon + telemetry → shows alerts and ML status  

Full diagram: `docs/ARCHITECTURE_AND_DETECTION.md`.

---

### Q9. Why Netlink instead of procfs or a device file?

**Answer:** Earlier versions (v0.4) used procfs circular buffers — **lossy and poll-based**. Netlink (v0.5+) provides:

- Structured binary events  
- Low overhead push model  
- Standard Linux IPC pattern for kernel→userspace security tools  

---

### Q10. Why a workqueue for cmdline capture?

**Answer:** The keyboard notifier runs in **atomic context** — cannot sleep or walk `mm_struct` safely. Cmdline extraction is deferred to `system_wq` with NULL checks for kernel threads.

---

### Q11. Why both heuristics AND machine learning?

**Answer:** **Complementary strengths:**

| Method | Strength | Weakness |
|--------|----------|----------|
| Heuristics | Immediate, interpretable, ties to PID | Miss subtle/multi-stage loggers |
| ML | Captures complex syscall/process patterns | Needs calibration; harder to explain |

Heuristics give **instant PID-level alerts** when the LKM sees direct input access. ML catches **telemetry-shaped attacks** (e.g., device scanning without triggering keyboard events yet).

---

## Part 4 — Machine Learning

### Q12. Describe your dataset.

**Answer:**

- **~93k rows** across L2–L4 Linux eBPF CSVs  
- **One benign + one malicious file per level**, captured on **different VMs** (`dataset/manifest.yaml`)  
- Features: kernel syscall deltas, keyboard interrupt counts, process mix, CPU/memory  
- **Excluded:** combined malicious-only CSV, Windows paths, leaky feature subsets  

Quality report: `docs/DATASET_QUALITY_REPORT.md`.

---

### Q13. What models did you use and why?

**Answer:** Per level, an **ensemble average** of:

1. **Random Forest** — robust baseline, handles mixed feature scales  
2. **Extra Trees** — more randomization, reduces overfit on tabular data  
3. **XGBoost** — strong gradient boosting for nonlinear boundaries  

**Hyperparameters (all levels):**

```
RandomForest / ExtraTrees: n_estimators=300, class_weight="balanced"
XGBoost: n_estimators=300, max_depth=6, learning_rate=0.1,
         subsample=0.9, colsample_bytree=0.9, scale_pos_weight=auto
```

Final probability = **mean** of three `predict_proba[:,1]` outputs.

---

### Q14. Your offline AUC is almost 1.0 — is the dataset trivial?

**Answer:** **Critical honesty for jury:**

- **Tier A** (row split within same capture session) → ~1.0 AUC — **optimistic upper bound**, not claimed as realistic  
- **Tier B** (cross-level) → still high — shows signal generalizes across levels  
- **Tier C** (cross-level + behavioral features only) → **macro AUC 0.75–0.99** — **thesis primary metric**  

Perfect Tier A results led to **leakage audits**: constant features, label-correlated columns, and filename artifacts were dropped (`train_ml.py` → `compute_leakage_safe_features`).

**Quote for defense:** *"We report Tier C because row-level splits on single-session captures overstate performance."*

---

### Q15. How does live ML differ from offline training?

**Answer:**

| Aspect | Offline | Live |
|--------|---------|------|
| Input | Historical CSV rows | `/tmp/fyp_telemetry_live.csv` tail |
| Labels | Known benign/malicious | **Unlabeled** — inference only |
| Baseline | Fixed train set | **20-row calibration** on local VM idle |
| Rules | None | Spikes, hysteresis, streak counters |
| Output | Metrics plots | `benign`/`malicious` + level |

Live system uses **`run_20260531_l2_hybrid`** bundle (tuned L2 + baseline L3/L4).

---

### Q16. What are ML Insights in the GUI?

**Answer:** Two sources:

1. **Offline** — `ml_insights_loader.py` reads `evaluation.json` (Tier A/B/C tables, feature lists)  
2. **Live** — panel shows current `per_level` scores, detection mode, confidence  

Use offline for **thesis numbers**; live for **demo truth**.

---

### Q17. Why did L4 false-alert at idle and how did you fix it?

**Answer:** Logs showed L4 ensemble **bimodal idle output** (~0.24 vs ~0.76) on the demo VM. When raw L4 crossed 0.5, `ml-L4` fired despite **adjusted delta ≈ 0**.

**Fixes (June 2026):**

- Raise L4 raw threshold to **0.82**  
- Require calibrated **delta ≥ 0.12**  
- Require **2 consecutive** ML hits  
- Disable alert **hold** for non-sim detections  
- Keep L4 syscall spikes **off** in default demo profile  

Evidence: `/tmp/fyp-demo/fyp_ml_decisions.log` before/after restart.

---

## Part 5 — Criticism & Limitations

### Q18. An attacker could kill your daemon or unload the module.

**Answer:** **Correct.** Prototype assumes **benign admin** installs the stack. Production hardening would need:

- Module signing / load pinning  
- Daemon systemd restart + integrity monitoring  
- Protected Netlink socket authorization  

Acknowledged as **future work** — FYP scope is proof-of-concept detection logic.

---

### Q19. Whitelist bypass — attacker names process `bash`.

**Answer:** Partial risk. Mitigations:

- Heuristic combo requires **rapid ratio** or **burst**, not name alone  
- ML uses **syscall/process features**, not only comm  
- Cmdline capture in kernel (future daemon use) improves attribution  

---

### Q20. VirtualBox / VM keyboard forwarding may skew events.

**Answer:** Documented in `docs/copilot_context.md`. Recommendation: demo typing **inside VM GUI**, not SSH-only sessions, for LKM events. ML telemetry path works regardless for unseen scripts.

---

### Q21. Small dataset — only two VMs per class?

**Answer:** Valid limitation. Mitigations attempted:

- Cross-level evaluation (train L2+L3, test L4)  
- Behavioral feature tier  
- **Unseen keylogger scripts** for live generalization demo  
- Supplement CSVs in `dataset/l2_supplement/`  

Future: session-ID-based splits and more capture diversity.

---

### Q22. Why not deep learning (LSTM on event sequences)?

**Answer:** Tabular ensemble models are **interpretable**, **fast on CPU**, and sufficient for ~93k row dataset. Sequential deep models need larger labeled session data and GPU infra — out of FYP time budget. Reasonable **engineering tradeoff**.

---

## Part 6 — Evaluation Strategy for Jury

### Recommended live sequence (15 minutes)

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | `sudo scripts/run_demo_verbose.sh` | Stack starts, logs tail |
| 2 | Wait 15–20 s | GUI: **System Clean**, calibrating → clean |
| 3 | Show Dashboard | LKM active, daemon running, ML scores informational |
| 4 | Open ML Insights | Offline Tier C metrics |
| 5 | Run `unseen2.py` (L2) | **Keylogger Detected**, alert with script PID |
| 6 | Stop script, wait ~10 s | Returns to **System Clean** |
| 7 | Optional: L4 syscall sim | Detection via telemetry spikes / ML |
| 8 | `bash scripts/export_demo_logs.sh` | Evidence bundle for appendix |

Detailed steps: `docs/LIVE_DEMO_GUIDE.md`.

---

### Questions jury might ask during demo

| If they ask… | You show… |
|--------------|-----------|
| "Is it recording my keys?" | Kernel struct / ETHICS.md — metadata only |
| "Prove ML not hardcoded" | `curl /health`, change artifact env, show `evaluation.json` |
| "What about false positives?" | Idle wait — **System Clean**; explain calibration + L4 guards |
| "Which process triggered it?" | Alerts tab — PID + `unseen2.py` name |
| "How fast?" | Detection within 1–3 s of script syscall activity |

---

## Part 7 — Quick Reference Card

| Topic | One-line answer |
|-------|-----------------|
| **Novelty** | Privacy-preserving LKM + dual heuristic/ML path + honest tiered eval |
| **Need** | Signature AV misses custom Linux keyloggers |
| ** vs AV** | Behavioral, zero-day capable, no hash needed |
| ** vs rkhunter** | Real-time input-stream focus, not file checks |
| **ML models** | RF + ExtraTrees + XGBoost ensemble per level |
| **Primary metric** | Tier C cross-level behavioral AUC |
| **Live demo** | ML telemetry on unseen scripts, clean at idle |
| **Main weakness** | Prototype integrity; limited dataset diversity |
| **Privacy** | No keystroke content captured |

---

## Part 8 — Suggested Jury Scoring Alignment

| Criterion | Evidence in project |
|-----------|---------------------|
| **Technical depth** | Custom LKM, Netlink, eBPF, FastAPI, Qt GUI |
| **Innovation** | Combined kernel + ML telemetry pipeline |
| **Completeness** | End-to-end runnable demo stack |
| **Documentation** | Architecture, ethics, testing, this Q&A |
| **Critical analysis** | Tiered eval, leakage drops, idle FP postmortem |
| **Presentation** | Live GUI + unseen script + log export |

---

**Related:** [`ARCHITECTURE_AND_DETECTION.md`](ARCHITECTURE_AND_DETECTION.md) | [`LIVE_DEMO_GUIDE.md`](LIVE_DEMO_GUIDE.md) | [`RESEARCH.md`](RESEARCH.md)

---

**End of jury evaluation guide**
