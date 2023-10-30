#!/bin/bash

PROJECT="fswatch-rclone"

# Sync latency / speed in seconds
LATENCY="10"

function usage() {
  cat <<End-of-message
    Usage : $0 [options] [--]

    Options:
    -s   source dir
    -t   rclone remote dir
    -h   Display this message
End-of-message
}

PID="$$"

LOCAL_PATH=""
TARGET=""
VERBOSE=""

while getopts "s:t:hv" OPT; do
  case $OPT in
  s) LOCAL_PATH=$OPTARG ;;
  t) TARGET=$OPTARG ;;
  v) VERBOSE="--verbose" ;;
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

# Check arguments
if [[ "$LOCAL_PATH" = "" || "$TARGET" = "" ]]; then
  usage
  exit
fi

# Welcome
echo ""
echo "Local source path:  \"$LOCAL_PATH\""
echo "Remote target path: \"$TARGET\""
echo ""

# first sync
rclone -v -P sync $LOCAL_PATH $TARGET

# Watch for changes and sync (exclude hidden files)
echo "Watching for changes. Quit anytime with Ctrl-C."
fswatch -o -r $VERBOSE -l $LATENCY $LOCAL_PATH |
  while read -r line; do
    rclone -v -P sync $LOCAL_PATH $TARGET
  done
