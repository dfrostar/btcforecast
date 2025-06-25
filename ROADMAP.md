# Project Roadmap

## Automation & Monitoring Improvements

### Quick Wins (To Be Implemented Immediately)
1. Add tqdm progress bars to model training for real-time feedback.
2. Add detailed logging (epoch metrics, errors) using Python's logging module.
3. Log training duration and metrics to a CSV file for later analysis.
4. Add resource usage logging (CPU, RAM) with psutil.
5. Add basic email notification on training completion or error.
6. Integrate smolagents for agentic automation (in progress, see agent_runner.py).

### Advanced Features (Future Work)
- Orchestrate multi-agent workflows (smolagents manager/worker agents).
- Integrate agent actions into app automation (e.g., trigger training, fetch logs, automate retraining).
- Integrate MLflow for experiment tracking and model versioning.
- Build a Streamlit dashboard for live monitoring and control.
- Automate retraining with Windows Task Scheduler or Airflow.
- Add Slack/Discord notifications.
- Cloud training and storage integration.

## [2025-06-24] Dependency Compatibility Update
- Pinned numpy to 1.24.4 and pandas_ta to 0.3.14b0 in requirements.txt to resolve ImportError with pandas_ta and technical indicators.
- Updated run_app.ps1 and run_enhanced_training.ps1 to always install dependencies before running.
- Users must always use the provided requirements.txt for a consistent environment.

## [2025-06-24] Conda Environment Adoption
- Added environment.yml for robust dependency management.
- Updated documentation to recommend Conda as the primary setup method.
- Pip/requirements.txt is now secondary and for advanced/non-Conda users only.

## References
- [Code Index](CODE_INDEX.md)
- [Document Index](DOCUMENT_INDEX.md)

---

*This roadmap is updated as features are added. See code and document indices for implementation details.* 