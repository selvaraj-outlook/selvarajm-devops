# Acme Platform Engineering Standards (sample)

## Regions
Production workloads may only run in the approved regions us-east-1 and eu-west-1.
Other regions require an exception from the cloud governance board.

## Incidents
For a SEV1 incident, the primary on-call engineer must acknowledge within 5 minutes.
If there is no acknowledgement, the incident escalates to the secondary on-call after 15 minutes.

## Databases
Production database schema changes are reviewed and approved by the data platform team
and must be applied through the migration pipeline, never by hand.
