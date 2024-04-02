#!/usr/bin/env bash

function usage() {
  cat <<End-of-message
    Usage : $0 [options] [--]

    Options:
    -r   check remote branch (default only check local branches)
    -c   current branch (default is master)
    -t   for test.  List all branches that need to be deleted.
    -f   filter for remote branch
    -x   for debug info
    -h   Display this message
End-of-message
}

REMOTE_BRANCH_FLAG=""
CURRENT_BRANCH_FLAG=""
TEST_FLAG=""
FILTER=""
DEBUG=""

while getopts "rctxf:h" OPT; do
  case $OPT in
  r) REMOTE_BRANCH_FLAG="true" ;;
  c) CURRENT_BRANCH_FLAG="true" ;;
  t) TEST_FLAG="true" ;;
  f) FILTER=$OPTARG ;;
  x) DEBUG="true" ;;
  h)
    usage
    exit 0
    ;;
  \?)
    echo -e "\n  Option does not exist : $OPTARG\n"
    usage
    exit 1
    ;;
  esac # --- end of case ---
done
shift $((OPTIND - 1))

EXCLUDE_BRANCH=("master")
DIFF_BRANCH="master"

if [[ -n "$CURRENT_BRANCH_FLAG" ]]; then
  DIFF_BRANCH=$(git branch | grep "\*" | awk '{print $2}')
fi
if [[ -n "$DEBUG" ]]; then
  echo "[DEBUG] diff branch: $DIFF_BRANCH"
fi
if [[ -z "$DIFF_BRANCH" ]]; then
  echo "[ERROR] find current branch fail:"
  git branch | grep "\*"
  exit 1
fi

if [[ "$DIFF_BRANCH" != "master" ]]; then
  EXCLUDE_BRANCH[1]=$DIFF_BRANCH
fi

if [[ -n "$DEBUG" ]]; then
  echo "[DEBUG] exclude branch: ${EXCLUDE_BRANCH[*]}"
fi

for ((i = 0; i < ${#EXCLUDE_BRANCH[@]}; i++)); do
  if [[ $i == 0 ]]; then
    EXCLUDE_BRANCH_REGEX="^\s*${EXCLUDE_BRANCH[i]}$"
  else
    EXCLUDE_BRANCH_REGEX="$EXCLUDE_BRANCH_REGEX|^\s*${EXCLUDE_BRANCH[i]}$"
  fi
done

MERGED_BRANCH=$(git br --merged "$DIFF_BRANCH" | grep -v -E "\*|\+" | grep -v -E "$EXCLUDE_BRANCH_REGEX")

if [[ -z "$MERGED_BRANCH" ]]; then
  echo "[INFO] Local Branch is Clean For $DIFF_BRANCH"
else
  echo "need delete local branches list for $DIFF_BRANCH:"
  echo "$MERGED_BRANCH"
  if [[ -z "$TEST_FLAG" ]]; then
    read -n1 -p "delete all branch(y/n):" -r answer
    echo ""
    case ${answer} in
    Y | y)
      for br in $MERGED_BRANCH; do
        git branch -D "$br"
      done
      ;;
    *)
      echo "abort delete!!"
      ;;
    esac
  fi
fi

if [[ -n "$REMOTE_BRANCH_FLAG" ]]; then
  for ((i = 0; i < ${#EXCLUDE_BRANCH[@]}; i++)); do
    if [[ $i == 0 ]]; then
      EXCLUDE_BRANCH_REGEX="^\s*origin/${EXCLUDE_BRANCH[i]}$"
    else
      EXCLUDE_BRANCH_REGEX="$EXCLUDE_BRANCH_REGEX|^\s*origin/${EXCLUDE_BRANCH[i]}$"
    fi
  done
  if [[ -z "$FILTER" ]]; then
    MERGED_BRANCH=$(git branch -r --merged "$DIFF_BRANCH" | grep -v -E "origin/HEAD|$EXCLUDE_BRANCH_REGEX")
  else
    MERGED_BRANCH=$(git branch -r --merged "$DIFF_BRANCH" | grep -v -E "origin/HEAD|$EXCLUDE_BRANCH_REGEX" | grep "$FILTER")
  fi
  if [[ -z "$MERGED_BRANCH" ]]; then
    echo "[INFO] Remote Branch is Clean For $DIFF_BRANCH"
  else
    echo "need delete remote branches list for $DIFF_BRANCH:"
    echo "$MERGED_BRANCH"
    if [[ -z "$TEST_FLAG" ]]; then
      read -n1 -p "delete all branch(y/n):" -r answer
      echo ""
      case ${answer} in
      Y | y)
        for br in $MERGED_BRANCH; do
          br=$(echo "$br" | sed "s/origin\///g")
          git push origin ":$br"
        done
        ;;
      *)
        echo "abort delete!!"
        ;;
      esac
    fi
  fi
fi
