#!/bin/bash

# Get the path we are in
SCRIPT=$(realpath "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

# Activate virtual environment
source "${SCRIPTPATH}/python3-venv/bin/activate"

# Launch app
cd "${SCRIPTPATH}/src"
echo "This terminal will show log messages of pmc-fdir"
python3 analysis_tool_gui.py

