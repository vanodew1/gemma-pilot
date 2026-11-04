# Glossary

The words this project uses, with one meaning each. Add to it when a new term comes up.

- **Issue**: the bug report text.
- **Task**: one issue plus the codebase at the buggy version.
- **Resolved**: the patch applies and that task's tests pass.
- **Patch**: the code change the agent produces.
- **Localization**: ranking which files need to change, measured by Hit@k.
- **Hit@k**: share of tasks where a file the real fix touched is in the top k.
- **Search words**: words used to search the code, picked by rules or by Gemma.
- **Attempt**: one write-patch-and-run-tests cycle; at most 3.
- **Retry clues**: text from a failing test run, fed into the next search.
- **Failing (model)**: proposed: Hit@1 not above K1 rules on the same issues.
- **Rules / K1**: the keyword extractor with fixed rules and no model.
- **K2**: Gemma writes the search words; the same scorer ranks the files.
- **Picking / S1**: Gemma chooses the file from the rules' top 5, shown as class and def outlines.
- **Memory probe / P**: Gemma names the file from the issue alone, with no file list or search.
- **Dev tasks**: the 129 public competition tasks (fastapi, rich, requests, httpx), with reference fixes.
- **Pilot issues**: the 55 old SWE-bench issues (requests, flask). Code checks only, never paper data.
- **Gold files**: non-test source files the reference fix touched.
