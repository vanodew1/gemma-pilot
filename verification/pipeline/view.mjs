const names = { locate: "Finding candidate files", select: "Model picks a file", edit: "Model writes an edit",
  test: "Running tests", finish: "Checking the diff", submitted: "Patch submitted" };
export const title = "E4B pipeline agent: one task under the tool-call cap";
export const state = (v) => (v.outcome === "scored" ? "All tasks scored" : names[v.phase]);
export const group = (v) => (v.outcome === "scored" || v.phase === "submitted" ? "done" : v.phase === "test" || v.phase === "edit" ? "fixing" : "finding");
export const colors = { finding: "blue", fixing: "orange", done: "teal" };
export const step = (a, f, t) => ({
  Locate: "search returns 5 candidates", Select: "model picks one",
  EditApplies: "edit applies", EditNoMatch: "edit doesn't match the code",
  TestPass: "tests pass", TestFail: "tests fail", CapHit: "tool-call cap reached",
  Finish: "test edits dropped, diff sent", NextTask: "next task starts", AllDone: "last task done", Stay: null,
}[a] ?? a);
