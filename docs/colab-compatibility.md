# Colab compatibility and validation

Validated on 2026-11-05 JST. Covers `MyPPSimulator_En.ipynb` and Beta 5.0.8. The March 2025 notebook and `beta-archive` are unchanged.

## First run

1. Open the notebook from the branch you want to use and enter your ScoreSaber `player_id`. Published notebooks leave this field blank.
2. Run **Input Information** to install the packages.
3. After installation finishes, restart the session once, then run all cells from the top. Colab can preload NumPy even in a fresh runtime. An initial `_no_nep50_warning` error after installation means the session needs this restart.
4. Review the Google Drive authorization. Use a separate data directory for the first run to protect existing data.

## Changes

- Replace old dependency pins with a combination validated on Python 3.13.
- Replace removed pandas APIs and use `iloc` for positional access inside row-wise Series callbacks.
- Parse ISO timestamps as UTC and update date-difference calculations.
- Fix score pagination and cache updates, including the final page and updated existing score IDs. Surface HTTP failures and invalid payloads instead of treating partial data as a completed fetch.
- Accept IPython event callback arguments.
- Give Beta's **Without Target Player Data** cell its own `filtered_plus_pp_min` input, so it no longer relies on the Target cell to define it.
- Remove execution outputs, counts and runtime metadata from published notebooks. Require an explicit player ID and preserve long IDs as strings.

## Validated dependencies

Actual Colab runtime: Python 3.13.18. The notebooks specify these primary dependencies; they do not lock every preinstalled Colab package.

| Package | Version |
|---|---|
| NumPy | 2.1.3 |
| pandas | 2.2.3 |
| Plotly | 5.24.1 |
| ipywidgets | 8.1.7 |
| GitPython | 3.1.45 |
| seaborn | 0.13.2 |
| SciPy | 1.16.3 |
| scikit-learn | 1.7.2 |
| XGBoost | 3.1.1 |

pandas 3 and Plotly 6 are not validated. Plotly rendering also needs access to its CDN.

## Validation scope

Real Colab validation used copies of the same calculation code with Drive mounting replaced by a dedicated temporary directory.

| Notebook | Result |
|---|---|
| Standard | Retrieved 5,591 public scores and used 4,677 ranked scores. PP calculations, curve/scatter output and an Acc-to-PP axis change succeeded. |
| Beta 5.0.8 | All 13 main code cells ran. Model training and prediction succeeded. Retrieved 1,973 ranked scores from 20 comparison players; generated a 38-song Target playlist and a 50-song Without Target playlist. Confirmed PP-axis rendering. |

Both generated JSON playlists were checked for song counts, hashes, matching level IDs and difficulty information. They were not tested inside BeatSaber. Model execution does not establish prediction quality for other players or future data.

Publication cleanup preserves the calculations. Offline tests additionally cover the blank-ID guard, long string IDs, syntax and removal of runtime metadata. Executed notebooks, personal scores, screenshots, generated playlists, caches and private Colab links are not committed.

Drive authentication, reuse of existing Drive data, every option combination and browser download completion remain unverified. External APIs and third-party map data may change or become unavailable.

## Offline checks

In an isolated Python 3.13 environment:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

Tests load the actual functions from both notebooks and use synthetic API responses. They cover final-page handling, cache boundaries, updated score IDs, HTTP failures, invalid payloads, empty accounts, input validation, notebook compilation and absence of saved execution data. They do not access the network or Drive.
