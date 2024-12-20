#!/bin/bash

# Check if data_path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <data_path>"
    exit 1
fi

DATA_PATH=$1
EXPERIMENT_NAME=$2
AE_METHODS="${@:3}"

PATH_TO_CODE=/home/user/code/BorealHDR

# Activate the virtual environment
source /home/user/.pyenv/versions/borealhdr/bin/activate

# Run the emulator_thread.py script with the provided data_path
python $PATH_TO_CODE/scripts/emulator_threads.py --dataset_folder $DATA_PATH --experiment $EXPERIMENT_NAME --automatic_exposure_techniques $AE_METHODS