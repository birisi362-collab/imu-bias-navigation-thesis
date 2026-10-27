# Project context

- This is Berkay's GTÜ master's thesis workspace for ground-vehicle IMU bias
  modelling, with GNSS-assisted online adaptation as a research goal.
- Current milestone: data inspection plus an initial raw-gyro quaternion diagnostic.
  A disjoint fixed-initial-offset comparison is also available. Read README.md,
  docs/FIRST_RUN.md, docs/ORIENTATION.md and docs/INITIAL_CORRECTION.md before
  extending the pipeline. This is not complete INS mechanization.
  docs/ROADMAP.md records scope.
- Explain changes in Turkish with the learning purpose; the user is learning
  mechanization, ESKF and ML alongside implementation.
- Use Python 3.11-compatible code and local path inputs; a virtual environment
  is optional. Run `python -m unittest discover -s tests -v` after relevant changes.
- Retain integer nanosecond timestamps. Never silently sort bad timestamps,
  extrapolate missing observations or reinterpret AHRS orientation as ground truth.
- Source reference trajectories are estimates, not exact physical bias labels.
- Keep data/raw and outputs out of git. Split training/validation/test by record;
  fit preprocessing on training only; causal test predictions must not see future data.
- During simulated GNSS outages, do not reset state using hidden reference data.
- Learned bias and ESKF bias states need one consistent correction convention.
  Do not subtract the same bias twice or report mechanization performance before
  time/frame conventions have been checked.
