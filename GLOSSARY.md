# Gemma 4 Developer Agent competition

Language for our effort to win the main track of Kaggle's Gemma 4 Developer Agent Competition.

## Language

### Scoring

**Hidden task**:
One of the roughly 120 tasks Kaggle scores a submission on, drawn from private repositories we never see.
_Avoid_: Test case, benchmark item

**Dev task**:
One of the 129 public tasks that come with a reference fix and its tests.
_Avoid_: Training task, instance, issue

**Resolved**:
A task whose submitted patch applies and passes that task's validation tests.
_Avoid_: Solved, fixed, passed

**Resolution rate**:
The share of hidden tasks a submission resolves; the competition's score.
_Avoid_: Accuracy, pass rate

### Competing

**Submission**:
One `submission.zip` sent to Kaggle, holding a complete agent configuration.
_Avoid_: Entry, run

**Final slot**:
One of the two submissions a team selects to count for prizes.
_Avoid_: Final pick, final entry

**Main slot**:
The final slot aimed at the highest main leaderboard score, using whichever allowed model does best.

**Small-model slot**:
The final slot aimed at the small-model bonus, which must use Gemma E2B or E4B.
_Avoid_: Bonus entry

**Win**:
Taking the highest possible place on the main leaderboard with the main slot, and the small-model bonus with the small-model slot.
_Avoid_: Paper prize, course grade
