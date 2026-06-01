#!/bin/bash
# Alias for verbose demo startup (multiplexed logs in terminal).
# See scripts/run_demo_verbose.sh for implementation.
exec "$(dirname "$0")/run_demo_verbose.sh" "$@"
