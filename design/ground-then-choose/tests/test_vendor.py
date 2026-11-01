"""Single source for the vendored ranking module.

1. skills/fix/scripts/ground.py is byte-identical to ground.py
   (tools/build_submission.py writes it; this test fails if someone edits either copy alone).
2. ground.py imports only the stdlib (parse its AST, compare top-level imports against
   sys.stdlib_module_names), so the sandbox copy can never grow a network or wheel dependency.
3. locate.show_menu(issue, repo) == ground.locate(...).render() + CHOICE_INSTRUCTION on a
   fixture repo, and that string is a suffix-block of choice_question(issue, menu).prompt:
   the agent sees what arm S1 measured.
"""
def test_vendored_copy_is_identical(): raise NotImplementedError
def test_ground_imports_only_stdlib(): raise NotImplementedError
def test_agent_menu_is_the_measured_menu(): raise NotImplementedError
