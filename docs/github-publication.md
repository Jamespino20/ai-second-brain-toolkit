# Proposed first private GitHub publication

Preparation does not authorize staging, committing, adding a remote or pushing.
Use only the separately reviewed exact file list and SHA-256 manifest. Keep those
machine-specific audit artifacts outside this repository.

Proposed name: `ai-second-brain-toolkit`. Visibility: **private**. Owner: the owner's
chosen personal GitHub account. Do not infer an organization or account from Git
identity. Do not initialize the remote with another README, license or gitignore.

## After explicit approval

From the existing local toolkit checkout:

1. Confirm the exact approved manifest still matches every byte and Git has no
   unexpected staged paths. Stop on any discrepancy; do not regenerate an approved
   list automatically. Check `gh auth status` and review the account and future Git
   author name/email. Do not print authentication tokens or add credentials to Git.
2. Stage only the approved literal paths, with Git's NUL-delimited pathspec-file
   support; review `git diff --cached --stat`, `git diff --cached --check` and the
   exact staged path list. Never use forced staging, broad `git add .` or `git add -A`.
3. Create the first local commit only after that review. Preserve existing main
   branch naming; no history rewrite is needed for this empty repository.
4. Create the private remote using `gh repo create ai-second-brain-toolkit --private
   --source=. --remote=origin`. This command does not include `--push`.
5. Check the returned repository owner/name and `isPrivate` before a separate
   approved `git push -u origin main`. Do not publish private audit evidence or
   configure GitHub secrets, capture hooks or external-memory access as a side effect.

Exact host-specific commands, the approved pathspec and hash manifest are supplied
in the private readiness report. Nothing in this guide was executed to create a
remote, commit or push during preparation.

Official command reference: https://cli.github.com/manual/gh_repo_create.
Without an OWNER prefix, GitHub CLI uses the authenticated user's account. Confirm
that account first; specify an explicit approved OWNER/name if needed.

## Limits of the review

Ignore patterns protect ordinary additions, not deliberate forced staging or future
files with unexpected names. The reviewed SHA-256 allowlist is the bounded initial
publication set. Secret/personal-data scanning is heuristic, supplemented by manual
review; it is not a proof that every possible credential form is detectable.

The repository has no original-code license selected. Third-party skill notices and
licenses must travel with their copies; they do not set the license of the toolkit's
original code. A broader reuse license is a separate owner choice.
