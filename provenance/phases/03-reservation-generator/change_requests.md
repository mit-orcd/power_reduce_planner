# Post-delivery change requests — Phase 03

## CR-03.1: add `SPEC_NODES` to the Flags list

> "can you add the following flag SPEC_NODES to the generated reservation"

Three spots updated:

- [`r9_pod_a_pipeline/make_reservation.py`](../../../make_reservation.py)
  line ~109 (the actual command builder string).
- Same file's module docstring.
- [`r9_pod_a_pipeline/README.md`](../../../README.md) "Slurm reservation
  command" section.

Verification: `Flags=MAINT,IGNORE_JOBS,SPEC_NODES` appeared in stdout.

## CR-03.2: undo CR-03.1

> "can you undo the SPEC_NODES that is not a flga a user sets, Slurm adds
> that"

Reverted the same three spots. Verified `Flags=MAINT,IGNORE_JOBS` again,
no `SPEC_NODES`.

**Domain note (worth recording for future sessions):** `SPEC_NODES` is an
internal Slurm flag set automatically on any reservation whose
`Nodes=` list names specific node names (versus a `NodeCnt=` /
feature-based reservation). Passing it explicitly to `scontrol create
reservation` is redundant and was likely to be rejected. Don't add it
back.
