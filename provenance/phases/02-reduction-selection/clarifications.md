# Clarifications (AskQuestion) for 02-reduction-selection

Each entry shows the question, the offered options, and the user's selection. User selections are looked up in the `KNOWN_ANSWERS` table inside `extract_session.py` because the transcript does not preserve them.

## Clarification #1
### Question `reduction_meaning`: What does 'bring the instantaneous max power down by 40%' mean precisely?

- **true_peak_reduction**: True peak reduction: after removal, the new instantaneous max for each cabinet (max over time of sum of remaining nodes) must be <= 60% of the original. The peak time is allowed to shift; we recompute on the remaining set. (Stronger guarantee, harder algorithm.)
- **at_peak_only**: At-original-peak only: remove nodes whose summed power AT the original peak time is >= 40% of the cabinet peak. Same as legacy select_nodes.py. The new instantaneous max may not actually drop by 40% if another timestamp was nearly as high. (Simpler.)
- **uniform_count**: Just remove ~40% of the nodes in each cabinet (count-based), regardless of power. Random subset of size ceil(0.4 * n_hosts). Power isn't part of the stop criterion.

**User answer:** at_peak_only

### Question `infeasible_behavior`: What should the script do if hitting the 40% target would force a partition below its minimum (i.e. infeasible under the partition constraint)?

- **best_effort_warn**: Best-effort: stop short of the 40% target for that cabinet, write the partial selection, print a warning listing the binding partitions. (Recommended)
- **hard_fail**: Hard fail: refuse to write any output, exit non-zero, and report which cabinets/partitions were infeasible.
- **retry_seeds**: Retry with different random seeds (configurable budget, e.g. 100 attempts per cabinet) and pick the best feasible outcome; only warn if no seed reaches 40% within the partition budget.

**User answer:** retry_seeds (user typed addendum: 'compute the partition constraint across all the cabinets. Use the 100 attempts for a limit to number of tries. Use the option with the least partition constraint violations if after 100 there is none outcome that meets the partition constraint.')

