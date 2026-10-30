from pilot import Keyword, extract_keywords, gold_files, hit_at_k, rank_files, recall_at_k

ISSUE = '''Calling `requests.get` with allow_redirects=False raises InvalidURL.

Traceback (most recent call last):
  File "/usr/lib/python3/site-packages/requests/sessions.py", line 12, in send
InvalidURL: "Failed to parse the redirect location"

The redirect should just be returned.
'''

PATCH = """diff --git a/requests/models.py b/requests/models.py
index 1..2 100644
--- a/requests/models.py
+++ b/requests/models.py
@@ -1 +1 @@
-a
+b
diff --git a/requests/utils.py b/requests/utils.py
--- a/requests/utils.py
+++ b/requests/utils.py
"""


def test_gold_files_are_the_files_named_in_diff_headers():
    assert gold_files(PATCH) == {"requests/models.py", "requests/utils.py"}


def test_keywords_are_tagged_by_where_they_came_from():
    kws = {(k.term, k.kind) for k in extract_keywords(ISSUE)}
    assert ("requests/sessions.py", "path") in kws
    assert ("send", "ident") in kws  # function named in the traceback frame
    assert ("InvalidURL", "ident") in kws
    assert ("allow_redirects", "ident") in kws
    assert ("Failed to parse the redirect location", "error") in kws
    assert ("redirect", "word") in kws


def test_stopwords_and_site_packages_noise_are_dropped():
    terms = {k.term for k in extract_keywords(ISSUE)}
    assert not terms & {"the", "should", "be", "site-packages", "usr", "lib", "python3"}


def test_each_term_appears_once_under_its_strongest_kind():
    kws = extract_keywords(ISSUE)
    terms = [k.term for k in kws]
    assert len(terms) == len(set(terms))
    assert next(k for k in kws if k.term == "InvalidURL").kind == "ident"


def kw(term, kind):
    return Keyword(term, kind)


def test_a_file_named_by_path_ranks_first():
    files = {
        "requests/sessions.py": "x = 1",
        "requests/models.py": "allow_redirects allow_redirects",
    }
    ranked = rank_files([kw("requests/sessions.py", "path"), kw("allow_redirects", "ident")], files)
    assert [f for f, _ in ranked] == ["requests/sessions.py", "requests/models.py"]


def test_identifier_hits_outrank_plain_word_hits():
    files = {"a.py": "location location location", "b.py": "allow_redirects"}
    ranked = rank_files([kw("location", "word"), kw("allow_redirects", "ident")], files)
    assert ranked[0][0] == "b.py"


def test_a_rare_term_beats_a_term_found_everywhere():
    files = {f"f{i}.py": "session" for i in range(9)}
    files["target.py"] = "rebuild_auth"
    files["f0.py"] += " session session"
    ranked = rank_files([kw("session", "ident"), kw("rebuild_auth", "ident")], files)
    assert ranked[0][0] == "target.py"


def test_matches_are_whole_words_and_files_without_hits_are_left_out():
    files = {"a.py": "sendall()", "b.py": "send()"}
    ranked = rank_files([kw("send", "ident")], files)
    assert [f for f, _ in ranked] == ["b.py"]


def test_hit_at_k_is_true_when_any_gold_file_is_in_the_top_k():
    ranked = ["a.py", "b.py", "c.py"]
    assert hit_at_k(ranked, {"b.py", "z.py"}, 2) is True
    assert hit_at_k(ranked, {"c.py"}, 2) is False
    assert hit_at_k([], {"c.py"}, 5) is False


def test_recall_at_k_is_the_share_of_gold_files_found():
    assert recall_at_k(["a.py", "b.py", "c.py"], {"a.py", "c.py", "z.py", "y.py"}, 3) == 0.5


def test_apostrophes_and_quoted_code_do_not_become_error_strings():
    text = 'I\'m not sure, but "args = utils.safe_encode_list(args)" fails and I\'d guess it\'s "a real message here".'
    errors = {k.term for k in extract_keywords(text) if k.kind == "error"}
    assert errors == {"a real message here"}


def test_contraction_stems_are_not_keywords():
    terms = {k.term for k in extract_keywords("It doesn't work and wouldn't ever.")}
    assert not terms & {"doesn", "wouldn"}


def test_the_file_that_defines_an_identifier_beats_files_that_only_use_it():
    files = {
        "app.py": "x.register_blueprint(bp)\n" * 6 + "register_blueprint()\n",
        "blueprints.py": "class Blueprint:\n    def register_blueprint(self):\n        pass\n",
    }
    ranked = rank_files([kw("register_blueprint", "ident")], files)
    assert ranked[0][0] == "blueprints.py"
