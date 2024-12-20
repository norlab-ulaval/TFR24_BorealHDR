#!/bin/bash

# Check if data_path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <data_path>"
    exit 1
fi

DATA_PATH=$1
EXPERIMENT_NAME=$2
AE_METHODS="${@:3}"

echo $AE_METHODS

PATH_TO_CODE=/home/user/code/scripts/visualization_tools

# Activate the virtual environment
source /home/user/.pyenv/versions/scripts_venv/bin/activate

# Run the emulator_thread.py script with the provided data_path
python $PATH_TO_CODE/thumbnail_emulation.py -i $DATA_PATH -x $EXPERIMENT_NAME -m $AE_METHODS