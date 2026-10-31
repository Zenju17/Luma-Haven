# Disaster recovery

Agree an RPO and RTO with the business; neither is currently established or verified. Confirm actual Supabase backup/PITR capability, retention, encryption and permissions. Periodically restore to an isolated project, verify constraints, representative booking/folio/payment workflows and reconciliation, and record elapsed time and data gap against the agreed objectives. Store runbooks and credentials securely outside the affected environment.

For corruption or failed deployment, stop affected writers, preserve evidence and establish the incident time. Restore to a separate project or recovery point, validate counts and financial consistency, reconcile later transactions and external payments, then plan a controlled cutover. Do not overwrite the only copy or assume rolling a schema migration backwards restores data. Rehearse credential compromise, loss of database access, accidental deletion, bad migration and provider outage.
