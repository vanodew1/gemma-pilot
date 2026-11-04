---- MODULE Pipeline ----
EXTENDS Naturals
CONSTANTS Tasks, Cap, MaxTries, Budget
\* One task at a time, as the harness runs them. Every tool call costs one time unit.
VARIABLES task, phase, calls, tries, patch, testsTouched, used, submitted, outcome
vars == <<task, phase, calls, tries, patch, testsTouched, used, submitted, outcome>>

Init == task = 1 /\ phase = "locate" /\ calls = 0 /\ tries = 0 /\ patch = "none"
        /\ testsTouched = FALSE /\ used = 0 /\ submitted = 0 /\ outcome = "running"

Running == phase \in {"locate", "select", "edit", "test"}
Spend == calls' = calls + 1 /\ used' = used + 1
Left == calls < Cap

Locate == phase = "locate" /\ Left /\ Spend /\ phase' = "select"
          /\ UNCHANGED <<task, tries, patch, testsTouched, submitted, outcome>>
Select == phase = "select" /\ Left /\ Spend /\ phase' = "edit"
          /\ UNCHANGED <<task, tries, patch, testsTouched, submitted, outcome>>
\* The model writes one SEARCH/REPLACE edit. It may not match, may be wrong, may touch a test file.
EditApplies == phase = "edit" /\ Left /\ Spend /\ tries' = tries + 1 /\ phase' = "test"
               /\ patch' \in {"good", "wrong"} /\ testsTouched' \in BOOLEAN
               /\ UNCHANGED <<task, submitted, outcome>>
EditNoMatch == phase = "edit" /\ Left /\ Spend /\ tries' = tries + 1
               /\ phase' = (IF tries + 1 < MaxTries THEN "edit" ELSE "finish")
               /\ UNCHANGED <<task, patch, testsTouched, submitted, outcome>>
TestPass == phase = "test" /\ Left /\ patch = "good" /\ Spend /\ phase' = "finish"
            /\ UNCHANGED <<task, tries, patch, testsTouched, submitted, outcome>>
TestFail == phase = "test" /\ Left /\ patch = "wrong" /\ Spend
            /\ phase' = (IF tries < MaxTries THEN "edit" ELSE "finish")
            /\ UNCHANGED <<task, tries, patch, testsTouched, submitted, outcome>>
\* The per-task cap stops the task wherever it is; the current diff goes to finish.
CapHit == Running /\ ~Left /\ phase' = "finish"
          /\ UNCHANGED <<task, calls, tries, patch, testsTouched, used, submitted, outcome>>
\* finish.py: drop test-file changes, submit the diff or NO_PATCH. Costs no model call.
Finish == phase = "finish" /\ phase' = "submitted" /\ testsTouched' = FALSE
          /\ submitted' = submitted + 1
          /\ UNCHANGED <<task, calls, tries, patch, used, outcome>>
NextTask == phase = "submitted" /\ task < Tasks /\ task' = task + 1 /\ phase' = "locate"
            /\ calls' = 0 /\ tries' = 0 /\ patch' = "none" /\ testsTouched' = FALSE
            /\ UNCHANGED <<used, submitted, outcome>>
AllDone == phase = "submitted" /\ task = Tasks /\ outcome = "running" /\ outcome' = "scored"
           /\ UNCHANGED <<task, phase, calls, tries, patch, testsTouched, used, submitted>>
Stay == outcome = "scored" /\ UNCHANGED vars

Next == Locate \/ Select \/ EditApplies \/ EditNoMatch \/ TestPass \/ TestFail
        \/ CapHit \/ Finish \/ NextTask \/ AllDone \/ Stay
Spec == Init /\ [][Next]_vars

\* Rules the reader signs off on
WithinTaskCap == calls <= Cap
WithinGlobalBudget == used <= Budget
TriesBounded == tries <= MaxTries
NoTestEditsSubmitted == phase = "submitted" => ~testsTouched
EveryTaskSubmitted == outcome = "scored" => submitted = Tasks
====
