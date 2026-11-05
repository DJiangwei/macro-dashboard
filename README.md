# Dashboard data branch

Build state for the macro dashboard: canonical frames, summaries and other
JSON artifacts (`output/`) and source caches (`data/`). Written by the
scheduled refresh; read by the Pages deploy, which rebuilds every page from
these files with `make rebuild-ui`. Do not commit code here.
