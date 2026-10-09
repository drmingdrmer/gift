# gift

[![Python package](https://github.com/drmingdrmer/gift/actions/workflows/python-package.yml/badge.svg)](https://github.com/drmingdrmer/gift/actions/workflows/python-package.yml)

gift is a fine tool working with mult-repo, multi-branch and multi-workdir.

# Install

gift needs [uv](https://docs.astral.sh/uv/), which installs gift's Python
dependencies on the first run. Put `gift` in a dir in `PATH`, and let `git`
call it, as the examples below assume:

```
git clone https://github.com/drmingdrmer/gift.git
ln -s "$PWD/gift/gift" ~/bin/gift
alias git=gift
```

gift passes every command to the `git` in `PATH`, and adds the `--sub`
commands.

# Usage

- A super repo to manage many sub repo
- Managing dependent repos

In a git working dir:
clone a sub repo into folder "path/to/subrepo"
```
git clone --sub https://github.com/drmingdrmer/gift.git@master path/to/subrepo
```

- Hacking with sub repo is just the same as working with a standard git repo:

    ```
    cd path/to/subrepo
    echo hello > world
    git add world
    git commit world -m 'say hi'
    ```

- Update sub repo changes to super repo
    <!-- TODO commit message -->
    ```
    cd -
    git commit --sub
    ```

## Enhanced commands

```
Clone url into sub repo.
git clone --sub

Commit only the content of the HEAD of a sub repo.
Ignores cached(staged) content or changes in work tree.
git commit --sub

git init --sub
git fetch --sub
git merge --sub
git reset --sub
```


## Setup sub repo

Setup every sub repo defined in `.gift`,
fetch from sub repo remote,
and checkout default branch.

```
git init --sub
```

## fetch latest sub repo, WITHOUT update work tree.

```
git fetch --sub

for each subrepo:
    git fetch <default-remote>

```

## Update sub repos to latest

```
git merge --sub

for each subrepo:
    git merge --ff-only <default-upstream>
```

## Put sub repo updates to super repo

```
git commit --sub
```

## Reset sub repo to the commit super repo expect.

```
git reset --sub [--soft|--mixed|--keep|--hard]

for each subrepo:
    git reset super/head
```

# Comparison to other solution

- git-submodule

- git-subtree

- git-subrepo by xp
- git-subrepo by https://github.com/ingydotnet/git-subrepo

#   Name

x

#   Status

This library is considered production ready.

#   Description



#   Author

Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>
