"""Reproducible one-off studies behind v2_results §10–§12.

Each module is runnable (`python -m pipeline.studies.<name>`) and states which
results section it backs. They sample from census cells, hydrate extra fields
via pull_prs.batch_pull where the census lacks them, and print the published
tables. Sampling is seeded — reruns reproduce the published draws exactly;
the API-hydration steps re-pull live (GitHub state may have moved since).
"""
