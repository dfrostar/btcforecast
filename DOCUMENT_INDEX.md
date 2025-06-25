# Document Index

- `README.md`: Project overview and setup instructions.
- `ROADMAP.md`: Project roadmap and planning.
- `CODE_INDEX.md`: Code index and references.
- `RECURSIVE_FORECASTING.md`: Details on recursive forecasting approach.

### Dependency Compatibility Note
- numpy is pinned to 1.24.4 and pandas_ta to 0.3.14b0 for technical indicator support.
- Always run scripts via run_app.ps1 or run_enhanced_training.ps1 to ensure dependencies are installed.

### Conda Environment Management
- Use `environment.yml` to create and manage your environment.
- Commands:
  - `conda env create -f environment.yml`
  - `conda activate btcforecast`
  - `conda env update -f environment.yml --prune`
- This ensures all dependencies are compatible and avoids pip/conda conflicts.

## Codebase Management
- See [CODE_INDEX.md](./CODE_INDEX.md) for a detailed, maintainable index of all code, scripts, and their purposes.
- Best practices: Update CODE_INDEX.md with every structural change, and use it as a navigation and onboarding tool for contributors. 