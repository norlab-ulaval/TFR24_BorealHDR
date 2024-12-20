#!/bin/bash

# Check if data_path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <data_path>"
    exit 1
fi

EXPERIMENT_NAME=$1
CAMERA_SETUP=$2
CALIB_FILE=$3
AE_METHOD=$4

PATH_TO_CODE=/home/user/code/ORB_SLAM2

# Navigate to the BorealHDR directory
cd $PATH_TO_CODE || { echo "Directory $PATH_TO_CODE not found"; exit 1; }

# Run ORB-SLAM2 Mono
if [ "$CAMERA_SETUP" == "mono" ]; then
    echo "Running Monocular"
    ./Main/mono/mono_borealhdr $PATH_TO_CODE/Vocabulary/ORBvoc.txt $PATH_TO_CODE/Main/mono/calib_files/$CALIB_FILE /home/user/code/BorealHDR/output/emulated_images/$EXPERIMENT_NAME/ae-$AE_METHOD/images_left/ ../results/mono/$EXPERIMENT_NAME/$AE_METHOD/

elif [ "$CAMERA_SETUP" == "stereo" ]; then
    echo "Running ORB-SLAM2 Stereo..."
    ./Main/stereo/stereo_borealhdr $PATH_TO_CODE/Vocabulary/ORBvoc.txt $PATH_TO_CODE/Main/stereo/calib_files/$CALIB_FILE /home/user/code/BorealHDR/output/emulated_images/$EXPERIMENT_NAME/ae-$AE_METHOD/images_left/ /home/user/code/BorealHDR/output/emulated_images/$EXPERIMENT_NAME/ae-$AE_METHOD/images_right/ ../results/stereo/$EXPERIMENT_NAME/$AE_METHOD/

else
    echo "Invalid camera setup. Please provide either 'mono' or 'stereo'."
    exit 1
fi