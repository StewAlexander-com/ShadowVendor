# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 14.x    | :white_check_mark: |
| < 14.0  | :x:                |

## Reporting a Vulnerability

**Do not** open public GitHub issues for security vulnerabilities.

Report vulnerabilities privately using one of the following:

- **GitHub Private Vulnerability Reporting** (preferred): [Create a security advisory](https://github.com/StewAlexander-com/ShadowVendor/security/advisories/new)
- **Email**: [stewart@stewalexander.com](mailto:stewart@stewalexander.com)

## In Scope

Please report issues in ShadowVendor itself, including:

- Remote code execution or command injection in the tool
- Path traversal or unsafe file handling
- Credential leakage or unsafe handling of secrets
- Supply-chain or dependency issues affecting shipped code

## Out of Scope

The following are not considered vulnerabilities in ShadowVendor:

- Operator misconfiguration or misuse of the tool
- Vulnerabilities in third-party OUI lookup APIs (`api.macvendors.com`, `api.maclookup.app`)
- Risks from opening generated HTML dashboards in a browser (Plotly loaded from CDN)
- Network data you choose to export to your SIEM or share externally

For privacy and network behavior (local processing, offline mode, optional API lookups), see the [README Security Considerations](README.md#-security-considerations) and [ADVANCED.md](ADVANCED.md#security--privacy).

## Response Expectations

- **Acknowledgment**: within 7 business days
- **Initial assessment**: within 14 business days
- **Disclosure**: coordinated disclosure preferred; we will work with reporters on timing
