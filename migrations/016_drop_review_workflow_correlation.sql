-- Drop the columns that linked a human review to a paused ADK workflow session.
--
-- Reviews used to pause a separate `tariff_monitoring_workflow` ADK app in the
-- worker, so each pending review carried the app, user, session, invocation and
-- interrupt of that pause (migration 007) plus the trace context to resume it
-- in another process (migration 014), and a reconciliation service repaired the
-- two stores when they disagreed.
--
-- The monitoring node now pauses the chat invocation itself: the pause lives in
-- the conversation's own ADK session, the reviewer answers it in the same
-- process, and every re-run of the node reads the review state from here. No
-- review needs to know which session paused on it, so nothing correlates the
-- two stores any more.
--
-- monitoring_runs.trace_parent stays: the worker still continues the trace of
-- the process that submitted a run.

ALTER TABLE human_reviews
    DROP COLUMN IF EXISTS workflow_app_name,
    DROP COLUMN IF EXISTS workflow_user_id,
    DROP COLUMN IF EXISTS workflow_session_id,
    DROP COLUMN IF EXISTS workflow_invocation_id,
    DROP COLUMN IF EXISTS workflow_interrupt_id,
    DROP COLUMN IF EXISTS trace_parent;
