# When the AI Can See the Experiment — Idea Record

**Historical source:** *When the AI Can See the Experiment: SUPER and the STEP Framework for Evidence-Grounded Collaborative Inquiry in Science Education* (September 2026 conceptual paper).

## Central thesis

The educational role of generative AI changes when it has **bounded access to the same instrument-derived evidence as the learner**. The AI is no longer merely an explainer outside the experiment; it can participate in an evidence-constrained inquiry cycle while measurement remains external to the model.

The paper explicitly presents this as a **conceptual and research framework**, not as an empirical claim of improved learning outcomes.

## STEP

**Sense → Test → Explain → Propose → repeat.**

- **Sense:** attend to the physical phenomenon through direct observation or instrumentation; preserve measurement provenance.
- **Test:** produce new evidence through measurement, repetition, intervention, or discriminating comparison.
- **Explain:** coordinate measurements, models, calculations and claims; fluent explanation is not evidence.
- **Propose:** choose the next evidence-producing move because of what has just been observed.

Shared evidence sits at the center of the cycle.

## SUPER

SUPER is the proposed low-cost evidence-sharing laboratory substrate. A common physical/instrument layer serves two clients:

1. a human-facing browser instrument/dashboard;
2. a machine-facing MCP/tool interface.

The AI does not manufacture the measurement. It receives sensor/instrument data produced outside the language model.

A representative internal capability layer might expose functions such as temperature reading, voltage/frequency measurement, waveform capture, I2C scan or bounded PWM. Human and AI interfaces should call the same logical instrument functions rather than evolving as unrelated products.

## The key design question

> What should a laboratory look like when intelligent assistance is assumed to be continuously available?

“Continuously available” is an **infrastructure assumption**, not a demand for continuous AI intervention. Intelligence can be immediately callable and context-aware while remaining quiet until useful.

## Design consequences

- learner and AI share a traceable measurement record;
- instruments describe capabilities in machine-readable form;
- measured, simulated, calculated and AI-inferred values remain distinguishable;
- AI is ambient but interruptible rather than incessant;
- consequential actions are bounded and authorized;
- physical limits are enforced in instrument/firmware layers rather than only in prompts;
- experimental context persists as questions branch;
- human-facing instruments remain fully useful without AI.

## Intellectual branching cost

The paper introduces **intellectual branching cost**: the instructional friction required to turn an unanticipated learner question into a scientifically coherent, evidence-producing extension of an ongoing investigation.

A major hypothesis is that shared instruments plus AI can lower this cost. The distance between **“I wonder what would happen if…”** and **“let us measure it”** becomes shorter.

This is proposed as more important than automation. The objective is to keep a moment of curiosity alive long enough to become a valid experiment.

## Worked pattern: Newtonian cooling

A simple cooling experiment can begin with temperature-versus-time measurement, create the need for a Newtonian model, and then branch into insulation, volume, container material, airflow or salinity.

The salinity branch illustrates the intended behavior: AI should not simply predict an answer. It should expose hidden design decisions—equal mass versus equal volume, density differences, probe depth, initial temperature, ambient conditions, repeated runs—and distinguish simple heat-capacity expectations from convection, evaporation and other mechanisms.

The bench experiment is a doorway to larger science, not proof of climate-scale mechanisms.

## Evidence boundary

A concise rule from the paper:

**The AI may interpret the evidence, but it may not manufacture the evidence.**

Simulation remains legitimate when explicitly labeled. Provenance should make measured, simulated, calculated and inferred quantities distinguishable.

## Authority boundary

- **Instrument:** authority over measurement under declared configuration; not scientific explanation.
- **AI:** synthesis, calculation, procedural alternatives and bounded tool coordination; not physical evidence or final judgement.
- **Learner:** question formation, interpretation, decisions and reflection; should not blindly delegate inquiry.
- **Teacher:** scaffolding, safety, coherence and assessment; need not predetermine every possible branch.

## Productive disagreement

The framework becomes educationally valuable when learner, AI and apparatus can disagree. If a prediction does not fit the measurements, the mismatch should generate a better question rather than be hidden. The physical system becomes a third party to the conversation.

## Research propositions

The paper proposes empirical tests around:

- number and quality of evidence-driven experimental branches;
- measurable/testable learner questions;
- ability to distinguish measurement, calculation, simulation and AI inference;
- willingness to revise models after contradiction;
- time/instructor effort needed to make a new branch runnable;
- learner agency under bounded versus unconstrained AI initiative.

A proposed three-condition study compares: structured dashboard only; dashboard plus ordinary AI chat without instrument access; and dashboard plus instrument-connected AI.

## Major risks

- AI errors can become physical actions.
- Fluent explanations can create false scientific confidence.
- Excessive AI initiative can turn inquiry into automated performance.
- sensors drift, lag and fail; measurement messiness must remain visible.
- networked instrumentation introduces privacy/security concerns.
- low-cost hardware alone does not guarantee equitable access.

## Design maxim

**Do not add AI to the laboratory as a separate attraction. Make the laboratory legible to AI. Then let AI earn its place by helping the learner ask, test and revise questions against real evidence.**

## Reconstruction path

A minimum research prototype needs only:

1. one networked low-cost controller;
2. one trustworthy physical sensor;
3. a visible human dashboard;
4. a small AI-facing tool surface exposing identity, sensor metadata, acquisition/logging and data retrieval;
5. provenance labels and timestamps;
6. a read-heavy AI interface with bounded write actions;
7. a simulator/digital twin exposing the same tool names;
8. logs sufficient to reconstruct who proposed and executed each experimental branch.

The durable contribution is the **evidence-sharing collaborative laboratory**, not one particular microcontroller or protocol implementation.
