# Project context

- This is Berkay's GTÜ master's thesis workspace for ground-vehicle IMU bias
  modelling, with GNSS-assisted online adaptation as a research goal.
- Current milestone: data inspection plus an initial raw-gyro quaternion diagnostic.
  A disjoint fixed-initial-offset comparison is also available.
  Fixed-latitude Earth-rate ablation: compare_earth_rate.py, docs/EARTH_RATE.md.
  Transport rate is still omitted; never call this full moving-ENU mechanization. Read README.md,
  docs/FIRST_RUN.md, docs/ORIENTATION.md and docs/INITIAL_CORRECTION.md before
  extending the pipeline. This is not complete INS mechanization.
  docs/ROADMAP.md records scope.
- Calibration-window sensitivity: compare_calibration_lengths.py and
  docs/CALIBRATION_LENGTHS.md. Always use a common evaluation start after the
  longest requested window, even if that window is rejected.
- Stop inventory/equal-window analysis: analyze_stationary_windows.py,
  docs/STATIONARY_WINDOWS.md. Reference-assisted OFFLINE selection must never
  be presented as a causal stop detector or physical bias ground truth.
- Post-stop comparison: compare_post_stop.py and docs/POST_STOP.md. Freeze all
  offsets before evaluation; use identical starts/durations/Earth models.
  Initial 5 s versus recent 20 s confounds window length and recency; never
  attribute improvement to physical bias drift alone.
- Age/length control: compare_calibration_factors.py and
  docs/CALIBRATION_FACTORS.md. Freeze old calibration at the first long stop;
  exclude that stop from recency evidence. Compare 5/20 s at matched future starts.
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
