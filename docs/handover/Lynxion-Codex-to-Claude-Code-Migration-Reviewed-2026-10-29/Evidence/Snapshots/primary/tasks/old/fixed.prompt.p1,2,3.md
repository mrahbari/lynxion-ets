# Lynxion ETS – SEV-1 Production Incident Reconstruction
# Unauthorized Order Placement, Missing Stop-Loss & Multi-Order Cascade
#
# ROLE
#
# Principal Software Architect
# Principal Trading Systems Engineer
# Principal Quant Engineer
# Production Incident Commander
# Senior Reliability Engineer
#
# PRIORITY
#
# SEV-1 (Highest Possible)
#
# STATUS
#
# PRODUCTION INCIDENT
# ROOT CAUSE UNKNOWN
# ZERO TRUST
# EVIDENCE DRIVEN
#
# DO NOT IMPLEMENT ANY CODE.
# DO NOT APPLY PATCHES.
# DO NOT PROPOSE REFACTORING.
#
# FIRST IDENTIFY THE TRUE ROOT CAUSE.
#
# ==================================================
# INCIDENT IS THE SOURCE OF TRUTH
# ==================================================
#
# Ignore every previous report that claimed:
#
# - VERIFIED
# - SAFE
# - FIXED
# - READY
#
# unless those conclusions can be reconciled with the
# observed production incident.
#
# If production behavior contradicts previous reports,
# production behavior is considered correct and previous
# conclusions are considered incomplete until proven otherwise.
#
# ==================================================
# OBSERVED PRODUCTION INCIDENT
# ==================================================
#
# The following behavior occurred in production:
#
# - Multiple consecutive XMRUSDT orders were opened.
# - Approximately 8 orders were opened within a short period.
# - Orders reached Stop Loss / full loss behavior.
# - Orders were opened without expected Telegram notifications.
# - Orders were opened without effective Stop Loss protection.
# - Previous "verified" safety reports failed to prevent this.
#
# Treat this incident as FACT.
#
# ==================================================
# PRIMARY OBJECTIVE
# ==================================================
#
# Reconstruct the complete incident.
#
# Your objective is NOT:
#
# - code review
# - architecture review
# - feature review
#
# Your objective IS:
#
# Explain exactly WHY this production incident happened.
#
# ==================================================
# REQUIRED INVESTIGATION
# ==================================================
#
# Reconstruct the complete execution timeline:
#
# Market Event
# →
# Watcher
# →
# Engine
# →
# Fusion
# →
# Strategy
# →
# Decision Pipeline
# →
# ExecutionIntent
# →
# Risk Enforcement
# →
# LiveExecutionGuard
# →
# Broker Adapter
# →
# Exchange
# →
# Reconciliation
# →
# Journal
# →
# Telegram
#
# At every stage identify:
#
# - expected behavior
# - observed behavior
# - actual code path
# - evidence
# - first divergence
#
# ==================================================
# TRACE EVERY EXECUTION PATH
# ==================================================
#
# Exhaustively locate every code path capable of:
#
# - place_order
# - submit_order
# - create_order
# - modify_order
# - cancel_order
# - broker.place*
# - broker.execute*
# - REST execution
# - websocket execution
# - retry logic
# - recovery logic
# - reconciliation logic
# - scheduled jobs
# - async tasks
# - background workers
# - emergency execution
#
# For EACH path produce:
#
# caller
# call stack
# authorization source
# risk validation
# stop-loss validation
# notification trigger
# journal update
# reconciliation hook
# final exchange call
#
# ==================================================
# FIND THE FIRST POINT OF FAILURE
# ==================================================
#
# Your goal is NOT to list symptoms.
#
# Your goal is to identify:
#
# The FIRST point where system behavior diverged from
# the intended architecture.
#
# Everything after that point is considered consequence,
# not root cause.
#
# ==================================================
# CHALLENGE EVERY SAFETY CLAIM
# ==================================================
#
# Previous reports claimed:
#
# - Single Order Gate
# - Mandatory Stop Loss
# - Risk Enforcement
# - LiveExecutionGuard
# - Reconciliation
#
# For EACH claim:
#
# Either:
#
# VERIFIED BY INCIDENT
#
# or
#
# CONTRADICTED BY INCIDENT
#
# Explain why.
#
# ==================================================
# SELF-CHALLENGE
# ==================================================
#
# Attempt to DISPROVE your own conclusions.
#
# Assume your first explanation is wrong.
#
# Search for:
#
# - race conditions
# - timing issues
# - duplicate execution
# - retry loops
# - reconciliation feedback loops
# - stale state
# - asynchronous ordering
# - broker API edge cases
# - exchange acknowledgement timing
#
# Continue until no more plausible explanations remain.
#
# ==================================================
# IMPLEMENTATION POLICY
# ==================================================
#
# DO NOT MODIFY CODE.
#
# DO NOT WRITE PATCHES.
#
# DO NOT DESIGN NEW ARCHITECTURE.
#
# If you believe a fix is required,
# first prove WHY the current design failed.
#
# ==================================================
# REQUIRED DELIVERABLE
# ==================================================
#
# Produce:
#
# 1. Complete incident timeline
# 2. Complete execution call graph
# 3. First point of failure
# 4. Root cause(s)
# 5. Contributing factors
# 6. Why previous fixes failed
# 7. Why previous audits missed the issue
# 8. Remaining unknowns
# 9. Evidence still required
#
# IMPORTANT
#
# Do NOT claim the system is safe.
#
# Do NOT claim the issue is fixed.
#
# Stop only after you can explain the observed production
# incident without contradiction.