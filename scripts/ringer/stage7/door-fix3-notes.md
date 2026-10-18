The prior harness stopped after one player command and recreated the 2B state
when attempting recovery. The continuation now keeps one RuntimeEngine/state,
records command 1 and conditionally requests exactly command 2, and never asks
again after a committed reveal. Eligibility was previously discarded before
serialization; each turn now stores explain_reveal eligibility, evidence,
matcher output, reasons, and before/after facts. Fresh bare-state emptiness is
explicitly recorded. Spend accounting previously used one mixed counter and
omitted continuation sends. A scoped _request adapter now reserves every
physical provider send, while player launches use a separate cap and event
kind. Live summaries and ledger rows carry experiment IDs and split counts.
The checker now accepts live artifacts, validates order, caps, evidence
recomputation, and ledger reconciliation; dry mode remains separate. Focused
tests, Ruff, Node syntax, and the 72-row dry check pass.
