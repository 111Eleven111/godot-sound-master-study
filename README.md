# godot-max-2d-platformer-AMS

Telemetry info stored at:
~/Library/Application\ Support/Godot/app_userdata/2D\ Platformer\ Template/telemetry

SRQ: How do observable gameplay behaviours correspond to players’ reported experiences of musicking and sonic agency?

Compare recorded behaviours such as:

number of jumps,
repeated platform sequences,
movement direction,
impact intensity,
time spent moving,
sound-triggering events,

(Se)

and deliberate interaction patterns,
with interview or questionnaire responses.

## Repeated-measures questionnaire analysis

`python-scripts/repeated_measures_analysis.py` reshapes the questionnaire into
participant/scenario/question observations and compares experience groups with
a participant-clustered bootstrap. It also attempts a Linear Mixed Effects
Model and Generalized Estimating Equation when `statsmodels` and `pandas` are
installed. By default it compares platforming-game experience levels 1-2 with
levels 3-4:

```sh
data/bin/python python-scripts/repeated_measures_analysis.py \
  --output repeated-measures-results.json \
  --plot-dir repeated-measures-plots
```

Use `--group participant_type` to compare participant categories instead.
Treat the output as exploratory: the sample is small and questionnaire ratings
are ordinal, so the bootstrap is the recommended baseline and model p-values
should not be treated as confirmatory evidence.

The plot directory also contains participant-level sonic-agency figures:
the composite by experience, the composite split by musical background, and a
scatter plot relating the composite to observed musicking events per minute.
The bootstrap plot shows the difference between group means for each item. The
red line is the observed difference, the dashed line is zero difference, and
the shaded region is the 95% bootstrap interval.

The model formula includes `scenario`, `play_position`, `group`,
`scenario:group`, and `question:group`. The interaction terms test whether
experience-group differences vary by scenario or are concentrated in particular
questionnaire items.

Telemetry group analysis
------------------------

`python-scripts/telemetry_group_analysis.py` compares participant-level
telemetry between experience levels 1-2 and 3-4. It reports audio-event,
sonification, musicking, jump, landing, far-fall, coin, and top-reach rates,
using participant-clustered bootstrap intervals and exploratory mixed models:

```sh
data/bin/python python-scripts/telemetry_group_analysis.py \
  --output telemetry-group-results.json
```

The script treats `far-fall` audio metadata as a fall-related proxy because
the current telemetry does not contain a separate `fall` event.
