# CODE_INDEX.md

## Overview
This document provides a structured, maintainable index of all major code, scripts, and documentation in the btcforecast project. Update this file with every major code or structure change.

---

## API
- `api/main.py` — FastAPI app entrypoint, defines REST endpoints for forecasting, training, evaluation, and health checks. Integrates data loading, feature engineering, and model operations.
- `api/__init__.py` — API package initializer.

## Data
- `data/data_loader.py` — Loads and preprocesses BTC data. Key: `load_btc_data()`
- `data/feature_engineering.py` — Adds technical indicators to data. Key: `add_technical_indicators()`
- `data/__init__.py` — Data package initializer.

## Models
- `models/bilstm_attention.py` — BiLSTM with attention model definition. Key: `train_ensemble_model`, `predict_with_ensemble`, `evaluate_ensemble_model`, `recursive_forecast`, `train_feature_forecasting_model`.
- `model.py` — Model architecture, training, and fallback logic. Key: `train_model`, `forecast_future`, `save_model_and_scaler`, `load_model_and_scaler`.

## Training
- `train_agent.py` — Main training script (basic version).
- `train_agent_enhanced.py` — Enhanced training with monitoring, logging, and notifications.
- `test_training.py` — Test script for training pipeline.

## Application & Automation
- `app.py` — Streamlit frontend dashboard.
- `run_app.ps1` — PowerShell script to start the app with environment checks.
- `run_enhanced_training.ps1` — PowerShell script for enhanced training.
- `agent_runner.py` — Entry point for agentic automation.
- `download_btc_history.py` — Script to download historical BTC data.

## Data, Models, and Outputs
- `btc_model.h5`, `btc_model.pkl` — Trained model files.
- `btc_scaler.pkl`, `btc_scaler.gz` — Data scaler files.
- `btc_forecast.csv` — Model forecast outputs.
- `training_results.json` — Training results summary.
- `training_metrics.csv` — Training metrics log.
- `training_resource_log.csv` — Resource usage log.
- `btc_training_log.csv` — Training log.
- `training_plots/` — Training visualizations.
- `logs/` — Log files.

## Configuration & Environment
- `environment.yml` — Conda environment specification (primary method).
- `requirements.txt` — Pip dependencies (secondary/legacy).
- `docker-compose.yml`, `Dockerfile` — Containerization configs.

## Documentation
- `README.md` — Main project overview and setup.
- `ROADMAP.md` — Project roadmap and milestones.
- `DOCUMENT_INDEX.md` — Index of all documentation files.
- `RECURSIVE_FORECASTING.md` — Technical details on recursive forecasting.

---

## Best Practices for Large Codebases
1. **Update this index with every PR that adds, removes, or refactors files.**
2. **For each file, briefly describe its purpose and key functions/classes.**
3. **Link to documentation and code sections for deeper dives.**
4. **Encourage contributors to maintain this file as part of the review process.**
5. **Automate checks (optional):** Use CI to remind or require updates to CODE_INDEX.md for structural changes.

---

_Last updated: 2025-06-24_ 