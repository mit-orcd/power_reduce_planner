# Clarifications (AskQuestion) for 07-self-containment-plus-plots

Each entry shows the question, the offered options, and the user's selection. User selections are looked up in the `KNOWN_ANSWERS` table inside `extract_session.py` because the transcript does not preserve them.

## Clarification #1
### Question `scontrol_location`: Where should `scontrol_show_node.json` live inside the repo to make it self-contained?

- **data_subdir**: r9_pod_a_pipeline/data/scontrol_show_node.json (standard 'data/' convention; clear that the repo carries a ~4 MB snapshot; default --scontrol-json updated accordingly)
- **repo_root**: r9_pod_a_pipeline/scontrol_show_node.json (at repo root next to README; flatter layout but mixes data with code at the top level)
- **no_copy_just_doc**: Don't copy: keep the file in telegraf_data/ but update DESIGN.md / SYSTEM_CARD.md to document how to fetch / produce it. Repo stays smaller but the external-dependency caveat stays.

**User answer:** data_subdir (with the user-typed addendum: 'Put the data in data/scontrol_show_node.json but compress it with gzip and have the read stage able to ingest either compressed or uncompressed.')

### Question `median_for_cumulative`: The legacy cumulative-power plot showed min / median / max curves. The new node_stats.csv currently has min / avg / max but no median. What do you want?

- **add_median**: Add median_power to sql/04_node_stats.sql and to export_node_stats.py; the cumulative plot then shows min / median / max (matches the original) and we can also show avg as a fourth curve. Tiny additive change to the existing CSV schema.
- **use_avg_only**: Skip median; the cumulative plot shows min / avg / max instead. Simpler (no schema bump) but the visualization differs subtly from the original (avg pulls higher than median when the distribution is right-skewed).
- **min_median_max_avg**: Add median AND show all four (min / avg / median / max) as separate curves. Most informative but the plot gets busier.

**User answer:** add_median

