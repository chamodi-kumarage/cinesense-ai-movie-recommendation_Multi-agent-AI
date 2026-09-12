# Step 5 Runtime Error Fixes

This revision addresses the runtime issues reported from the planner logs:

- Fixed a race condition that could create the same `active_profiles.user_id` twice when Planner Insights, Weekly Summary, and Calendar Status load in parallel on a fresh account.
- Made default/active profile initialization idempotent and recovery-safe after a concurrent insert.
- Hardened `/api/plan` request normalization so transient blank/null numeric values from browser controls no longer cause repeated HTTP 422 responses.
- Added frontend clamping/normalization for planner minutes and buffer values and blocked duplicate plan submissions while a request is already running.
- Improved API validation error messages so the UI shows readable field errors instead of raw validation objects.
- Kept the existing Free-plan scheduler restriction; the UI now explains the Premium/Family requirement more clearly when HTTP 429 is returned.

Note: 401 responses before login are expected for protected endpoints. A 400 response for an invalid calendar busy slot is also expected validation behavior; valid slots continue to save normally.
