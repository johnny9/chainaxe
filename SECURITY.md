# Security and Safety Policy

ChainAxe controls high-power mining hardware. A defect can cause overheating,
fan loss, hashboard damage, fire, or unsafe behavior even though the controller
itself accepts only low-voltage input. Treat fan control, thermal shutdown,
power sequencing, and hashboard communication as safety-relevant functions.

## Reporting a vulnerability

Do not open a public issue for an exploitable vulnerability or for a failure
that could create an immediate electrical or thermal hazard. Use the repository
owner's private GitHub security-advisory form:

<https://github.com/johnny9/chainaxe/security/advisories/new>

Include the affected revision, firmware version or commit, exact hashboard and
fan models, reproduction steps, expected behavior, actual behavior, and any
logs or measurements that can be shared safely. Remove wallet credentials,
pool credentials, Wi-Fi credentials, serial numbers, and other secrets.

If private advisories are unavailable, contact the repository owner through a
private channel listed on the `johnny9` GitHub profile.
Do not send credentials or seed material.

## Supported versions

No production release is currently supported. The design is pre-prototype and
must be treated as untested. After the first release, this section will list the
maintained hardware and firmware revisions.

## Safety issues that are not vulnerabilities

Report non-exploitable documentation errors, component-selection concerns, and
ordinary design defects in the public issue tracker. If disclosure could put an
installed system at risk, use the private advisory process first.
