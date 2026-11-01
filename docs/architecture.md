# Architecture

```mermaid
flowchart LR
    A[Olist CSV files<br/>data/raw, unchanged] --> B[Python cleaning pipeline<br/>src/clean_data.py + tests]
    B --> C[data/processed<br/>validated tables]
    C --> D[PostgreSQL staging<br/>src/load_staging.py]
    D --> E[analytics schema<br/>dimensions, facts, views]
    E --> F[SQL query library]
    E --> G[Pandas analysis<br/>EDA, RFM, cohorts, delivery]
    E --> H[Power BI report<br/>7 pages + drill-through]
    E --> I[ML dataset<br/>leakage-safe features]
    I --> J[Late-delivery model<br/>train / validation / test by time]
    B --> K[Independent reconciliation<br/>src/reconcile.py]
    E --> L[Integration tests + QA cards]
```

Layers: ingestion and cleaning (Python), storage and modelling (PostgreSQL), analysis (SQL, Pandas), presentation (Power BI), prediction (scikit-learn), assurance (pytest, reconciliation, QA cards).