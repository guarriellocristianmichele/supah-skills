# Controlling false positives in ai-slop-prose

Researched 2026-11-13 from primary sources. Basis for `scripts/calibrate.py`, the verdict learning in `skills/ai-slop-prose/scripts/learn.py`, and the context gates in `scan.py`. Numeric defaults marked *(ours)* are proposals to validate with the calibration protocol, not literature values.

## 1. Document thresholds: conformal, calibrated on human text

- Word counts are overdispersed (Poisson mixtures, negative binomial as the gamma case; Church & Gale 1995). Corpus-level tests such as Dunning's G² "overestimate significance"; per-text tests are recommended ([Lijffijt et al.](https://core.ac.uk/download/34098391.pdf); [Kilgarriff 2001](https://www.academia.edu/1541464/Comparing_Corpora)). One "delves" in 400 words gets a huge G² against a large reference, so G² cannot be the per-document test.
- Keep G² (`2·Σ O·ln(O/E)`, critical values 3.84 / 6.63 / 10.83 / 15.13 for p < .05 / .01 / .001 / .0001, [UCREL](https://ucrel.lancs.ac.uk/llwizard.html)) and Log Ratio only to build and rank word lists from a human-vs-AI contrast.
- Per document, use a **split-conformal p-value**: with human calibration scores s₁..sₙ, `p = (1 + #{sᵢ ≥ s}) / (n + 1)`; flag when `p ≤ α`. This guarantees `P(flag | human) ≤ α` under exchangeability ([Angelopoulos & Bates](https://arxiv.org/abs/2107.07511); conformal p-values are marginally valid and positively dependent, [Bates et al.](https://arxiv.org/abs/2104.08279)).
- Stratify by language × genre × length bucket (<150, 150–400, 400–1000, >1000 words) *(ours)*, or exchangeability breaks. `n ≥ 1/α − 1` for a finite threshold; aim for ≥ 1000 human documents per stratum. Defaults *(ours)*: α = 0.01 per document, 0.005 for W metrics.
- A distribution-free confidence interval for a corpus quantile comes from order statistics with Binomial(n, q) indices.

## 2. Many rules, one decision

- Neyman–Pearson: the likelihood ratio is most powerful at fixed FPR. Naive-Bayes approximation over rule counts: `log LR = Σ_r [c_r·ln(λ_AI,r/λ_H,r) − L·(λ_AI,r − λ_H,r)]`. Its nominal p-value is not trustworthy; calibrate it conformally.
- Fisher and Stouffer assume independent rules; tells co-occur, so they are anti-conservative.
- A **conformal max statistic** (each rule's density as its human-corpus rank, maximum over rules, calibrated on human documents) controls the per-document any-flag rate at α under any dependence. Bonferroni is valid but costs recall; Benjamini–Yekutieli is valid under dependence; BH across documents sharing a calibration set is valid (Bates et al.).

## 3. Learning rule precision from verdicts

- Labels: `tell` (rewritten), `kept` (a real tell, kept for a reason), `fp` (not a tell). Only `fp` lowers precision.
- Beta-Binomial per rule. Empirical-Bayes prior per tier from observed precisions (`α₀+β₀ = m(1−m)/v − 1`, `α₀ = m(α₀+β₀)`), strength capped at 10; fallbacks S Beta(9,1), M Beta(3,1), W Beta(1,1) *(ours)*.
- Demote S→M→W→off when `P(precision < target) > 0.95`; promote when the 95% lower bound exceeds the target. Targets S 0.95, M 0.75 *(ours)*. No change before 30 verdicts: by the rule of three, 0 failures in n gives a 95% upper bound ≈ 3/n ([Hanley & Lippman-Hand](https://jamanetwork.com/journals/jama/article-abstract/389714)), so precision ≥ 0.90 needs ≥ 30 clean verdicts, ≥ 0.97 needs ≥ 100.
- Drift: discount on each verdict, `α ← γα + TP`, `β ← γβ + FP`, γ = 0.99 (discounted Thompson sampling, [Raj & Kalyani](https://arxiv.org/abs/1707.09727)).
- Keep demoted rules learnable: sample θ ~ Beta(α, β) and still show a hit when θ exceeds the target.
- The reviewer is an LLM, and LLMs recognise and favour their own generations ([Panickssery et al.](https://arxiv.org/abs/2404.13076)): have a human confirm a random 5–10% of `fp` verdicts, and treat LLM verdicts as noisy labels.

## 4. Context gates

- Hard exclusions: code, blockquotes and quoted speech, headings and titles, proper nouns ("Delve" as a name), domain terms; in Italian, dashes that open dialogue lines.
- A learned suppressor (multinomial naive Bayes, Laplace smoothing, ±5-token window plus section type and in-quote flag) only after ≥ 200 labelled hits per rule family with ≥ 30 per class *(ours)*; it may only suppress hits, never create them; evaluate on a time-ordered split. With one dominant user, shrink per-user offsets toward a global model.

## 5. The Kobak list is a population instrument

- Kobak et al. computed yearly frequency `p = (a+1)/(b+1)`, counterfactual `q = p₋₂ + 2·max(p₋₂ − p₋₃, 0)`, gap `δ = p − q`, ratio `r = p/q`, over words with `p > 10⁻⁴` ([arXiv 2406.07016](https://arxiv.org/abs/2406.07016)). Their 13.5% figure is a lower bound at corpus level.
- Score distinct excess words per 1k words, not single words; weight common words by δ and rare ones by r; calibrate conformally.
- The list drifts both ways: people now say "delve" more in speech ([Yakura et al.](https://arxiv.org/abs/2409.01754)); "delve" fell in arXiv abstracts after it was publicised while "significant" kept rising ([Geng & Trotta](https://arxiv.org/abs/2502.09606)). Recalibrate yearly on verified post-2023 human text.

## 6. What the detection literature says about false positives

- Uncalibrated thresholds fail: at the 0.5 default, RAID measured FPRs of 99.3% (GLTR), 96.0% (LLMDet), 23.2% (Fast-DetectGPT); calibrate in-domain and report recall at fixed FPR ([RAID](https://arxiv.org/abs/2405.07940)).
- Domain shift breaks detectors ([M4](https://arxiv.org/abs/2305.14902)); Biber-feature random forests reach 93–98% on one model but label 9.8% of human texts as LLM in the 7-way task ([Reinhart et al.](https://arxiv.org/abs/2410.16107)).
- Non-native writers: seven perplexity detectors flagged TOEFL essays at 61.22% average FPR ([Liang et al. 2023](https://arxiv.org/abs/2304.02819)). Rare-word rules are less exposed (AI essays have more lexical diversity, [Herbold et al.](https://arxiv.org/abs/2304.14276)); connector and formula rules are more exposed. Calibrate a non-native stratum.
- Short texts: Turnitin requires 300 words and reports < 1% document FPR above a 20% AI share, about 4% at sentence level ([Turnitin](https://www.turnitin.co.uk/blog/understanding-the-false-positive-rate-for-sentences-of-our-ai-writing-detection-capability)); OpenAI's classifier reached 26% recall at 9% FPR before it was withdrawn. Suppress W metrics below about 150 words.
- Paraphrase defeats detectors (DIPPER cut DetectGPT from 70.3% to 4.6% at 1% FPR, [Krishna et al.](https://arxiv.org/abs/2303.13408)): accept limited recall rather than tightening thresholds against human text.
- Expert humans who use LLMs misclassified 1 of 300 articles by majority vote, mostly from vocabulary cues ([Russell et al.](https://arxiv.org/abs/2501.15654)): keep a model in the loop for judgement.
- Italian: no excess-vocabulary study exists yet (TU Dresden's Generate-IT started Sept 2025). Translating the English list is invalid; build Italian lists from an Italian corpus contrast at lemma level. Machine-translated EN→IT text uses a narrower set of equivalents and can look LLM-like ([Trapella et al.](https://aclanthology.org/2026.stygenai-1.7.pdf)). The long dash is standard in Italian dialogue and asides.

## 7. Calibration protocol

1. Per language: ≥ 1000 human documents over ≥ 5 genres (mostly before Nov 2022, about 20% verified post-2023, plus non-native English and machine-translated Italian strata) and ≥ 1000 topic-matched AI documents from ≥ 3 model families, including LLM-edited text. Split 50% calibration, 20% tuning, 30% holdout, stratified.
2. Store per document: length, sentences, count per rule.
3. Per rule: human and AI hit rates per document with Wilson intervals, `LR = a/h`, PPV at prior π: `π·a / (π·a + (1−π)·h)`.
4. Admission *(ours)*: S needs Wilson upper bound of h ≤ 0.5% and LR ≥ 20; M needs LR ≥ 5; otherwise W or dropped.
5. Conformal thresholds per stratum for each W metric and for the document score.
6. Holdout: human false positives k of n, Clopper–Pearson upper bound ≤ 2α to pass; report AI recall at that FPR.

## Not verified

The sign in Kobak's ratio threshold as extracted (`log10 r > (log10 2/4)·log10 p`, likely a lost minus sign); the Beta law of realised conformal FPR and Sadasivan's AUROC bound (recalled, not re-fetched); full texts of Jiang et al., Desaire et al. and Granger & Tyson; any primary FPR for sentence-length CV alone.
