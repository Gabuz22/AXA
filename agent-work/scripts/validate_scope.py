#!/usr/bin/env python3
"""Garde-fou de périmètre (protection compensatoire — CONTRAINTE GITHUB).

GitHub Actions ne peut pas restreindre un jeton d'écriture à un seul dossier. Ce script est la
protection compensatoire : AVANT tout commit, il liste les fichiers modifiés (git) et refuse si
l'un d'eux sort de l'allowlist. Au moindre fichier interdit : affiche, échoue, aucun commit.

Usage :
  python agent-work/scripts/validate_scope.py                 # runs autonomes : agent-work/ uniquement
  python agent-work/scripts/validate_scope.py --allow-install # installation initiale : + .github/workflows, CODEOWNERS

Sortie : code 0 si tout est dans le périmètre, 1 sinon (fail-closed).
"""
import sys, subprocess, argparse
import safety_checks as S


def changed_files(root):
    """Union des fichiers modifiés : indexés, non indexés, non suivis.

    IMPORTANT : sortie `-z` (séparateur NUL), qui n'est JAMAIS quotée ni échappée par git. Sans cela, git
    entoure de guillemets et échappe en octal les noms contenant des caractères non-ASCII/spéciaux (accents,
    parenthèses, tiret cadratin), ce qui faisait échouer à tort le contrôle de périmètre sur des fichiers
    pourtant sous agent-work/ (ex. les fiches Inspecteur « essenciel_(assurance_obsèques).json »)."""
    files = set()
    for cmd in (["git", "diff", "--cached", "--name-only", "-z"],
                ["git", "diff", "--name-only", "-z"],
                ["git", "ls-files", "--others", "--exclude-standard", "-z"]):
        try:
            out = subprocess.run(cmd, cwd=root, capture_output=True, timeout=60)   # bytes (pas text=)
        except Exception as e:
            raise S.SafetyError("git indisponible pour le contrôle de périmètre : %s" % e)
        # décodage UTF-8 explicite (les noms de fichiers git sont en UTF-8 ; ne pas dépendre de la locale).
        for line in out.stdout.decode("utf-8", "surrogateescape").split("\0"):
            line = line.strip()
            if line:
                files.add(line)
    return sorted(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-install", action="store_true",
                    help="autorise en plus .github/workflows, CODEOWNERS (installation initiale uniquement)")
    args = ap.parse_args()

    policies = S.load_policies()
    allowlist = policies.get("install_time_allowlist" if args.allow_install else "write_allowlist", [])

    files = changed_files(S.REPO_ROOT)
    if not files:
        print("[scope] Aucun fichier modifié.")
        return 0

    offenders, unsafe = [], []
    for f in files:
        if not S.is_safe_relpath(f):
            unsafe.append(f)
        elif not S.path_in_allowlist(f, allowlist):
            offenders.append(f)

    print("[scope] Fichiers modifiés : %d — allowlist : %s" % (len(files), ", ".join(allowlist)))
    for f in files:
        tag = "INTERDIT" if (f in offenders or f in unsafe) else "ok"
        print("  [%s] %s" % (tag, f))

    if unsafe:
        print("\n[scope] ÉCHEC : chemins non sûrs (absolu/`..`/backslash) : %s" % ", ".join(unsafe))
    if offenders:
        print("\n[scope] ÉCHEC : fichiers hors périmètre autorisé : %s" % ", ".join(offenders))
    if offenders or unsafe:
        print("[scope] Aucun commit ne doit être créé (fail-closed).")
        return 1
    print("[scope] OK — tous les changements sont dans le périmètre autorisé.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except S.SafetyError as e:
        print("[scope] SafetyError : %s" % e)
        sys.exit(1)
