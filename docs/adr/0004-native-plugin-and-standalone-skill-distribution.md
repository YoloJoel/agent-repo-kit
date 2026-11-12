# 0004: Native plugin and standalone Skill distribution

Status: Accepted

## Context

Users want a Claude Code plugin or standard Skills installation, then one repository
initialization invocation. A URL instruction/source bootstrap still exposes developer
setup as the user-facing product and does not make a copied Skill self-contained.

## Decision

Ship native .claude-plugin/plugin.json and marketplace.json with root skills/ folders.
Package the initialization helper, the same runtime and checksum-bound text resources
inside initialize-repo. Native installers own Skill lifecycle; project initialization
records skill_delivery=installed and writes project rules/runtime without duplicate Skills.
Retain source bootstrap and Python packaging only for development/compatibility.

Keep canonical workflows as WORKFLOW.md under runtime assets and generate only three real
root SKILL.md files. Embed consumer workflow resources as JSON text so installers do not
discover duplicate nested Skills. Check generated artifacts against source in CI.

## Alternatives

- Use a source checkout or README prompt as the main entry: does not meet native installation.
- Reference files outside a Skill folder: fails when an installer copies only that folder.
- Share scripts through sibling Skills: creates an undeclared installation dependency.
- Hand-maintain native and Python implementations: introduces behavior/resource drift.

## Consequences

Installers copy/cache complete Skill folders; Python 3.11+ is required only when executing
the check runtime. Claude uses namespaced Skills, while other hosts use standard discovery.
Plugin manifests and actual installer behavior must be tested independently of runtime tests.
Runtime trust and real model invocation remain distinct states. The custom marketplace is
the supported distribution route; submission to an official plugin directory is out of scope.

## Supersession

Supersedes ADR-0003's source-first user entry. Its no-global-CLI and repository-local
runtime guarantees remain; the source bootstrap is now a compatibility path.
