# Tiers and thresholds come from corpora, and isolated medium hits are not required fixes

The scanner's tiers and density thresholds are no longer hand-picked: `scripts/calibrate.py` measures every rule on about 5,200 human (pre-2022) and AI documents in English and Italian, admits a tier only when the Wilson 95% upper bound of its human document hit rate is low enough (S ≤ 0.5%, M ≤ 1%) and, where the AI corpus is representative, when its likelihood ratio is high enough, and sets each density threshold by split-conformal calibration on human text with a language-wide fallback. Calibration can only lower a tier. A single medium (M) rule in otherwise clean text is reported as W (visible, not a required fix); a document needs one S hit or two distinct M rules. On the 30% holdout this leaves 4/592 English and 4/455 Italian human documents with any required fix (95% upper bounds 1.54% and 2.00%), against 25.6% of English AI documents.

## Considered options

- Hand-tuned thresholds: rejected; the first calibration showed `not-x-but-y` hitting 7% of human documents and Italian en dashes tripping the dash metric in 120 human texts.
- Likelihood ratios for Italian: rejected for now; the only Italian AI corpus is a Llama-2 model fine-tuned to imitate human news.
- α = 0.002: rejected; Italian calibration strata are too small (n < 499), so thresholds fell back to defaults and the Italian false positive rate rose to 25%.

## Consequences

- Any change to a rule or lexicon is followed by `python scripts/calibrate.py run && python scripts/calibrate.py report`, and the new `calibration.json` and results note are committed with it.
- Recall is deliberately traded for precision; the reviewing model still reads every W hit.
