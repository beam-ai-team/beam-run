# Beam Run operations — learning-hub

Generated from `beam/contracts/operations.yaml`. Prefer MCP; on an unavailable or malformed tool, use the mapped CLI command. Reconcile an ambiguous write before retrying.

| Operation | Safety | MCP | CLI fallback | Confirmation | Verify |
| --- | --- | --- | --- | --- | --- |
| learning.issues | read | optimizeTool | `beam learning issues <agentId>` | none | not-required |
| learning.issue | read | getToolOptimizationStatus | `beam learning issue <agentId> <issueId>` | none | not-required |
| learning.feedbacks | read | lh_get_issue_feedbacks | `beam learning feedbacks <agentId> <issueId>` | none | not-required |
| learning.issue-jobs | read | lh_get_issue_jobs | `beam learning issue-jobs <agentId> <issueId>` | none | not-required |
| learning.trend | read | lh_get_accuracy_trend | `beam learning trend <agentId> [startDate endDate]` | none | not-required |
| learning.tools | read | lh_get_learning_tools | `beam learning tools <agentId>` | none | not-required |
| learning.tool | read | lh_get_tool_detail | `beam learning tool <agentId> <toolFunctionName>` | none | not-required |
| learning.config | read | lh_get_tuner_config | `beam learning config <agentId>` | none | not-required |
| learning.set-config | reversible-write | lh_set_tuner_config | `beam learning set-config <agentId> <payloadFile> --confirm <agentId>` | always-two-turn | learning.config |
| learning.submit-feedback | additive-write | lh_submit_feedback | `beam learning submit-feedback <payloadFile>` | none | not-required |
| learning.submit-task-feedback | additive-write | lh_submit_task_feedback | `beam learning submit-task-feedback <payloadFile>` | none | not-required |
| learning.merge | destructive-write | lh_merge_issues | `beam learning merge <payloadFile> --confirm merge` | always-two-turn | not-required |
| learning.optimize | external-effect | optimizeTool | `beam learning optimize <agentId> <issueId> --confirm <issueId>` | always | not-required |
| learning.discard | destructive-write | lh_discard_issue | `beam learning discard <agentId> <issueId> --confirm <issueId>` | always-two-turn | not-required |
| learning.job | read | getToolOptimizationStatus | `beam learning job <threadId>` | none | not-required |
| learning.approve-job | external-effect | lh_approve_job | `beam learning approve-job <threadId> --confirm <threadId>` | always-two-turn | learning.job |
| learning.reject-job | destructive-write | lh_reject_job | `beam learning reject-job <threadId> --keep-feedbacks <true|false> --confirm <threadId>` | always-two-turn | learning.job |
| learning.reoptimize-job | external-effect | lh_reoptimize_job | `beam learning reoptimize-job <threadId> --feedback <text> --confirm <threadId>` | always-two-turn | learning.job |
| learning.cancel-job | destructive-write | lh_cancel_job | `beam learning cancel-job <threadId> --confirm <threadId>` | always-two-turn | learning.job |
| learning.run-job | external-effect | lh_run_job | `beam learning run-job <threadId> --confirm <threadId>` | always-two-turn | learning.job |
| learning.resume | external-effect | lh_resume_on_hold_jobs | `beam learning resume <agentId> --confirm <agentId>` | always-two-turn | learning.issues |
