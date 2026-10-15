# Security policy

## Reporting a vulnerability

Report it privately: on this repository's **Security** tab, choose **Report a vulnerability**.
Please do not open a public issue or pull request for it. Say what you found, how to reproduce it,
and what it exposes.

The integration holds a Honeycomb API key and sends a home's events to Honeycomb, so a flaw that
leaks the key, or sends what a user excluded, is a vulnerability.

## Supported versions

The latest [release](https://github.com/alejandroerickson/honeycomb-hacs/releases).

## How the repository is checked

The checks that keep secrets and private material out of this repository are in
[security checks](okf/operations/security-checks.md).
