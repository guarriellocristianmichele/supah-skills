# Public corpora of LLM-written code

Researched 2026-11-14. Basis for the AI side of the code-scanner calibration: rule hit rates on human code against AI code, per language. Every dataset below was fetched without a token through the Hugging Face datasets-server (`/splits`, `/size`, `/rows`, `/filter`, `/statistics`) or a direct `resolve/main/` or GitHub release URL; field names, label values and counts come from those responses, not from the cards. Re-check before relying on a count: these repositories still change.

## Verified datasets

| Dataset | Languages | Models | Year | Size | License | Code field | Label fields | Access that worked |
|---|---|---|---|---|---|---|---|---|
| [HanxiGuo/CodeMirage](https://huggingface.co/datasets/HanxiGuo/CodeMirage) | Python, JavaScript, Java, C, C++, C#, Go, Ruby, PHP, HTML | claude-3.5-haiku, gpt-4o-mini, o3-mini, deepseek-v3, deepseek-r1, gemini-2.0-flash, gemini-2.0-flash-thinking-exp, gemini-2.0-pro-exp, llama3.3-70b, qwen2.5-coder | 2025 | train 146,992, test 62,996; per language 700 human + about 1,400 per model in train | CC BY-NC-ND 4.0 | `code` (whole files, median 2,956 chars) | `source` (`Human` or model), `language`, `variant` (`Normal`, `Paraphrased`, null for human) | `/rows` and `/filter` on config `default`, splits `train`, `test`; `resolve/main/train.csv` (493 MB) and `test.csv` |
| [project-droid/DroidCollection](https://huggingface.co/datasets/project-droid/DroidCollection) | Python, JavaScript, Java, C, C++, C#, Go, PHP, Rust | 43 generators: GPT-4o, GPT-4o-mini, Qwen2.5-Coder 1.5B to 32B, Qwen2.5-72B, Llama 3.1/3.2/3.3, DeepSeek-Coder, CodeLlama, Phi-3/3.5, Yi-Coder, Granite, CodeGemma, Mistral Small, StarCoder | 2025 | train 846,598, dev 105,824, test 105,826 | none on the card or the paper page | `Code` (median 913 chars) | `Label` (`HUMAN_GENERATED`, `MACHINE_GENERATED`, `MACHINE_REFINED`, `MACHINE_GENERATED_ADVERSARIAL`), `Generator`, `Model_Family`, `Language`, `Source`, `Generation_Mode` | `/rows`, `/filter` on config `default`, splits `train`, `dev`, `test` |
| [DaniilOr/SemEval-2026-Task13](https://huggingface.co/datasets/DaniilOr/SemEval-2026-Task13) | config C: Python, JavaScript, Java, C, C++, C#, Go, PHP; config A trains on Python, Java, C++ only | same generator pool as DroidCollection plus Gemma 3, Gemini 2.0 Flash Lite, Qwen3, DeepSeek-R1, Devstral | 2025 | A 500k/100k/1k, B 500k/100k/1k, C 900k/200k/1k | Apache-2.0 | `code` | `label` (C: 0 human, 1 machine, 2 hybrid, 3 adversarial, per [`task_C/label_to_id.json`](https://github.com/mbzuai-nlp/SemEval-2026-Task13)), `generator`, `language` | `/rows`, `/filter` on configs `A`, `B`, `C`, splits `train`, `validation`, `test` |
| [OSS-forge/HumanVsAICode](https://huggingface.co/datasets/OSS-forge/HumanVsAICode) | Python (285,249), Java (221,795) | gpt-3.5-turbo (April 2023), DeepSeek-Coder-Instruct 33B, Qwen2.5-Coder-Instruct 32B | 2025 | 507,045 rows, each one human function and three AI functions for the same docstring | CC BY-SA 4.0 | `human_code`, `chatgpt_code`, `dsc_code`, `qwen_code` (the card says `deepseek_code`; the file says `dsc_code`) | `hm_index` prefix `gp` Python, `gj` Java; `docstring` is the prompt | `resolve/main/python_dataset.jsonl` (652 MB, rows in shuffled order, stream and stop); `/rows` on `default`/`train` mixes both languages |
| [DaniilOr/CoDET-M4](https://huggingface.co/datasets/DaniilOr/CoDET-M4) | Python, Java, C++ | GPT-4o (`gpt`), CodeLlama 7B, Llama 3.1 8B, CodeQwen 1.5 7B, Nxcode-orpo 7B | 2025 | 500,552 (Python 185,163; 232,634 human, 254,331 AI overall) | MIT | `code` (with comments), `cleaned_code` (comments and docstrings removed by the authors) | `model` (`human`, `gpt`, `codellama`, `llama3.1`, `qwen1.5`, `nxcode`), `target` (`human`, `ai`), `language`, `source` (`gh`, `lc`, `cf`), `split` | `/rows`, `/filter` on `default`/`train` |
| [serafeimdossas/ai-code-detection](https://huggingface.co/datasets/serafeimdossas/ai-code-detection) | Python | Claude 3.5 Haiku, OpenAI o4-mini, Gemini 2.5 Flash-Lite (2,048 each) | 2025 | 11,827 (5,684 human) | MIT | `code` | `label` (`Human_written`, `Ai_generated`), `generator`, `task_name`, `source` (`Rosetta Code`, `CodeNet`) | `/rows` on `default`/`train` |
| [basakdemirok/AIGCodeSet](https://huggingface.co/datasets/basakdemirok/AIGCodeSet) | Python | Codestral, Gemini, CodeLlama | 2024 | 2,828 AI rows in `created_dataset_with_llms.csv`, of which 941 written from scratch; human CodeNet submissions in `human_selected_dataset.csv` | CDLA-Permissive-2.0 | `code` | `LLM`, `status_in_folder` (`Generate`, `Wrong`, `Runtime`), `problem_id`, `label` | `resolve/main/data/*.csv`; `/rows` on `default`/`train`; `/statistics` returned 500 |
| [isThisYouLLM/H-AIRosettaMP](https://huggingface.co/datasets/isThisYouLLM/H-AIRosettaMP) | 10 incl. Python 13,737 and JavaScript 10,065 rows | StarCoder2 (translations from another language's Rosetta solution) | 2024 | 121,247 | MIT | `code` | `target` (`Human_written`, `Ai_generated`), `language_name`, `set` (for example `Python_from_Go`) | `/rows`, `/statistics` on `default`/`train` |
| [BigCodeBench samples](https://github.com/bigcode-project/bigcodebench/releases/tag/v0.2.5) | Python | 244 JSONL files from about 120 models, among them claude-3-5-sonnet-20240620, claude-3-opus, gpt-4o, gpt-4o-mini, o1, o3-mini, gemini-1.5/2.0, DeepSeek-V3, Llama 3.1 405B | 2024-2025 | 1,140 tasks per full run, 148 per hard run | Apache-2.0 | `solution` in each JSONL line | model in the file name, `task_id` | `sanitized_calibrated_samples.zip` (165 MB); stdlib `zipfile` over HTTP Range requests reads one member without the whole archive |
| [EvalPlus samples](https://github.com/evalplus/evalplus/releases/tag/v0.2.0) | Python | gpt-4-1106-preview, gpt-3.5-turbo, DeepSeek-Coder, CodeLlama, others | 2023 | 399 MBPP+ tasks per model | Apache-2.0 | one `.py` file per task | model in the zip name, task in the path | release zips, same Range trick |

Counts measured with `/filter` on DroidCollection `train`: Python `MACHINE_GENERATED` from `STARCODER_DATA` 8,824 against 16,694 human; JavaScript `MACHINE_GENERATED` 19,218 in all, 12,216 from `STARCODER_DATA`, 5,287 from `DROID_PERSONAHUB`, against 24,150 human from `STARCODER_DATA`; GPT-4o alone gives 3,536 Python and 3,224 JavaScript rows. On SemEval config C `train`: JavaScript has 38,277 human, 20,460 machine and 9,247 adversarial rows; GPT-4o gives 2,422 Python and 2,222 JavaScript machine rows.

## What each one is good for

CodeMirage is the closest match to the scanner's use. The human side is 1,000 files per language (700 train, 300 test) from CodeParrot github-code-clean, sanitized in May 2022, so it predates assistants. Each AI file was regenerated from a summary of one human file, with the original line count and length in the prompt and a BLEU ceiling of 0.5, which gives ten length-matched AI files per human file ([paper](https://arxiv.org/abs/2506.11059), NeurIPS 2025 datasets track). The first Python row of the `gpt-4o-mini` block is a rewrite of the first Python human row (the same Home Assistant EnOcean sensor), so rows look aligned by position inside each source and language block; the card does not document this. Rows come in contiguous blocks of one language, source and variant (each 100-row page we read was 97 to 100% one block), but the block order is not simply by source or by language, so locate blocks with `/filter` or by probing offsets. The license forbids redistributing modified copies: keep fetched files in the ignored `.calibration/` directory and commit only counts.

DroidCollection is the largest pool with JavaScript and named open models. Its `Source` field lets both sides come from the same domain: `STARCODER_DATA` is GitHub code from StarCoderData (The Stack v1.2, crawled in 2022), and the card says AI rows were written from instructions inferred from human code, from docstrings, or from personas. Algorithmic sources (`TACO`, `LEETCODE`, `CODEFORCES`, `ATCODER`) are short stdin scripts and should be excluded or kept in their own stratum. Many generations ran with `max_tokens` 512 (see `Sampling_Params`): in a 1,000-row random sample (only 3 to 25 rows per cell, so a hint, not a measurement), `STARCODER_DATA` AI files had a median of 26 lines (Python) and 30 (JavaScript) against 53 and 40 for human files, so drop rows that fail to parse and compare rates per line or per function, not per file. The Vault sources hold only human, refined and adversarial rows. Rows are shuffled within large blocks, and the last block is all adversarial. The card carries no license, and neither does the arXiv page of the [Droid paper](https://arxiv.org/abs/2507.10583) (EMNLP 2025).

SemEval-2026 Task 13 republishes the same pipeline's data under Apache-2.0, by the same authors. Config C is the only one with JavaScript in train. It has no `Source` field, so the domain cannot be matched; label 2 (hybrid) and 3 (adversarial) must be dropped.

OSS-forge HumanVsAICode is the one large set with human and AI code for the same task, function by function, which suits wrapper, re-raise and defensive-check rules. The human side is CodeSearchNet (2019) with the docstring removed into `docstring`; AI functions sometimes repeat that docstring, and some are stubs (`# Implementation goes here`). Strip docstrings on both sides before comment rules and drop bodies under three statements. Use `qwen_code` and `dsc_code`; `chatgpt_code` is GPT-3.5.

BigCodeBench has the most recent closed models (Claude 3.5 Sonnet, GPT-4o, o1, o3-mini) writing whole Python functions, but no clean human side: its canonical solutions were written with LLM help and then refined by people ([paper](https://arxiv.org/abs/2406.15877)). Use it only as an extra AI stratum. The `instruct` folder holds code written from a natural-language prompt; `calibrated` files have the prompt's imports and signature prepended.

## Rejected

| Dataset | Reason |
|---|---|
| [AICD-bench/AICD-Bench](https://huggingface.co/datasets/AICD-bench/AICD-Bench) (2026) | rows hold only `code` and `label`: no language, no generator; no license on the card |
| [mahirlabibdihan/GPTSniffer](https://huggingface.co/datasets/mahirlabibdihan/GPTSniffer) | Java only, ChatGPT (2023), loose `.java` files; datasets-server `/splits` returned 500 |
| [HungPhamBKCS/magecode-dataset](https://huggingface.co/datasets/HungPhamBKCS/magecode-dataset) | fields are `task_id`, `code`, `label` only: no model; C++/Java/Python competitive code; no license |
| [Aanimated/HMCorp](https://huggingface.co/datasets/Aanimated/HMCorp) | `text` and `generated` only, no model or language; ChatGPT 3.5 functions; superseded by OSS-forge HumanVsAICode, which extends it |
| [MultiAIGCD](https://github.com/BasakDemirok/MultiAIGCD) | Claude 3.5 Sonnet v2, GPT-4o, o3-mini, DeepSeek-V3 and others in Python, Java, Go, but the README says the data archive "is not yet published" |
| H-AIRosettaMP | AI side is StarCoder2 translating another language's solution, not a chat model writing code; Rosetta human code contains U+00A0 in place of blank-line spaces, which breaks `ast.parse` unless replaced |
| AIGCodeSet | Python only, CodeNet stdin scripts (median 15 lines), two thirds are repairs of human code; keep only as a short-script check |
| CoDET-M4 for JavaScript | no JavaScript; for Python it adds GPT-4o and four 7B to 8B models, but DroidCollection covers them with more domains |
| serafeimdossas/ai-code-detection as a main source | recent models but short Rosetta and CodeNet programs; useful as a small paired Python check, not as the main pool |
| EvalPlus samples as a main source | 399 short MBPP functions per model and GPT-4 Turbo at best; human MBPP reference code exists but the set is small |
| TypeScript in any of the above | none of the verified datasets labels TypeScript; CodeMirage JavaScript files sometimes use ES module syntax, nothing more |

## Recommendation

Python, about 1,000 documents per side per source:

1. CodeMirage: all 1,000 human Python files (train and test) against 1,000 AI files, `variant='Normal'`, 100 per model.
2. DroidCollection, `Source='STARCODER_DATA'`: 1,000 `HUMAN_GENERATED` against 1,000 `MACHINE_GENERATED`, stratified by `Model_Family` and capped at 150 per family, keeping instruct models. If the missing license matters, take the AI side from SemEval config C (`label=1`) and accept the unmatched domain.
3. OSS-forge HumanVsAICode: 1,000 Python pairs (`hm_index` starting `gp`), human against `qwen_code`, with `dsc_code` as a second AI column, docstrings stripped on both sides.

JavaScript, about 1,000 per side per source:

1. CodeMirage: all 1,000 human JavaScript files against 1,000 AI files, `variant='Normal'`, 100 per model.
2. DroidCollection, `Source='STARCODER_DATA'`, `Language='JavaScript'`: 1,000 human against 1,000 machine, stratified by family as above.

TypeScript has no public labelled corpus here; build its human side from pre-2022 repositories and treat any AI side as unmeasured.

## Fetch notes

- `/rows` takes at most `length=100` and answered every call; `/filter` with `where="Language"='JavaScript' AND "Label"='MACHINE_GENERATED'` worked but often returned 500 ("dataset index is loading", "Authentication check ... timed out"). Retry with backoff, or page `/rows` and filter in the script.
- Anonymous requests are rate limited: after a few hundred quick calls from parallel scripts, `/rows` returned HTTP 429 with an HTML body. Keep one request in flight and sleep on 429.
- Quote column names in `where` with double quotes; DroidCollection columns are capitalised (`Code`, `Language`), the others are lower case.
- Parquet files are not readable with the standard library; every source above has a stdlib route (rows JSON, JSONL, CSV or zip).
