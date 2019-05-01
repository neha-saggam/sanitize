#!/usr/bin/env python
"""Sanitizes a change before its pushed to Gerrit"""
import argparse
import os
import subprocess
import sys
from stat import S_ISREG

import git


class RawDescAndDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    pass


PARSER = argparse.ArgumentParser(
    description="""Sanitizes C++ code as per Tarana C++ coding guidelines:
  - Fix #define guards in header files.
  - Fix file name in copyright information.
  - Remove trailing white spaces from lines.
  - Remove trailing blank lines from files.
  - Format code using clang-format.
  - Format BUILD files using buildifier.""",
    usage="%(prog)s [-h] <Directories to process (default: .)>",
    epilog="",
    formatter_class=RawDescAndDefaultsHelpFormatter,
)

PARSER.add_argument(
    "-m",
    "--modified-only",
    help="process only the files modified in git.",
    default=False,
    action="store_true",
)
PARSER.add_argument("dirs", nargs="*", default=".",
                    help="Directories to process")

ARGS = PARSER.parse_args()
FNAME_ATT = "@file "
CHANGED_FILES = set()

def is_modified(f_path):
    """Checks if a file is modified in git"""
    return os.path.normpath(f_path) in CHANGED_FILES


def main():
    for a_dir in set(ARGS.dirs):
        if not os.path.exists(a_dir):
            print("%s does not exit" % a_dir)
            exit(1)

        # Gets the list of files modified in the current commit
        if ARGS.modified_only:
            repo = git.Repo(a_dir, search_parent_directories=True)
            CHANGED_FILES.update(
                set(repo.git.diff(name_only=True).splitlines()))

    for a_dir in set(ARGS.dirs):
        a_dir = os.path.relpath(a_dir, ".")
        git_repo_home = git.Repo(
            a_dir, search_parent_directories=True).working_tree_dir
        repo_home_prefix = os.path.relpath(
            a_dir, git_repo_home).replace(a_dir, "")

        for root, dirs, files in os.walk(a_dir):
            for f in files:
                file_name = f
                rel_path = os.path.normpath(os.path.join(root, f))

                if ARGS.modified_only and not is_modified(os.path.join(repo_home_prefix, rel_path)):
                    continue

                f = os.path.abspath(rel_path)
                # A file (e.g file may not exist)
                if not os.path.exists(f):
                    print("%s does not exist or not a regular file" % f)
                    continue

                with open(f, "r") as fl:
                    lines = fl.readlines()

                if not lines:
                    print("File %s is empty!" % (rel_path))
                    continue

                # Remove trailing blank lines
                fix_trail = False
                print(lines[-1])
                while lines[-1] == "\n":
                    fix_trail = True
                    lines.pop()

                # Write back the files
                with open(f, "w") as fout:
                    for line_no, line in enumerate(lines):
                        if f.lower().endswith((".js", ".jsx")) and line.find("console.log") != -1:
                            print("Loggers found at %d in %s" %(line_no + 1, f))
                        # Remove trailing whitespace
                        line.rstrip("\n")
                        fout.write(line)
                    if fix_trail:
                        print("Trailing empty lines removed from %s" %
                              (rel_path))

                # Run clang-format
                # if f.lower().endswith((".hpp", ".h", ".cpp", ".cc", ".proto")):
                #     subprocess.Popen(
                #         "clang-format -i %s" % (rel_path), shell=True, stdout=subprocess.PIPE
                #     )


main()
