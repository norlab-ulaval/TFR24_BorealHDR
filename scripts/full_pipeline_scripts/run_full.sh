#!/bin/bash

# PARAMS
deployment="campus-09-25-2023"
camera_setup="stereo"
calib_file="$camera_setup-april-2023.yaml"
experiment="backpack_2023-09-25-15-05-03"

methods_all=("fixed" "drl_exposure_ctrl" "shim" "zhang" "classical-30" "classical-50" "classical-70" "kim" "wang")
# Divide the methods into two groups to save threads
methods_orb_1=("fixed" "drl_exposure_ctrl" "shim" "zhang")
methods_orb_2=("classical-30" "classical-50" "classical-70" "kim" "wang")

BOOL_EMULTAION=true
BOOL_ORBSLAM2=true
BOOL_SAVEVIDEO=true

# Directory containing the folders
DATA_DIR="/home/user/code/BorealHDR/data_sample/"
EMULATION_DIR="/home/user/code/BorealHDR/output/emulated_images/"

echo "############################################################################"
echo "Processing $deployment: $experiment"
echo "############################################################################"

# Run the emulation script
if [ "$BOOL_EMULTAION" = true ]; then
    echo "--------------------------------------------------"
    echo "Running the emulation..."
    /home/user/code/scripts/full_pipeline_scripts/run_emulation.sh $DATA_DIR $experiment "${methods_all[@]}"
    echo "Emulation complete."
    echo "--------------------------------------------------"
fi

# Run the ORB-SLAM2 script
if [ "$BOOL_ORBSLAM2" = true ]; then
    echo "--------------------------------------------------"
    echo "Running ORBSLAM2..."
    for method1 in "${methods_orb_1[@]}"; do
        echo "Running ORBSLAM2 with method: $method"
        /home/user/code/scripts/full_pipeline_scripts/run_orbslam2.sh $experiment $camera_setup $calib_file $method1 &
    done
    # Wait for all background processes to finish
    wait
    for method2 in "${methods_orb_2[@]}"; do
        echo "Running ORBSLAM2 with method: $method"
        /home/user/code/scripts/full_pipeline_scripts/run_orbslam2.sh $experiment $camera_setup $calib_file $method2 &
    done
    # Wait for all background processes to finish
    wait
    echo "ORBSLAM2 complete."
    echo "--------------------------------------------------"
fi

if [ "$BOOL_SAVEVIDEO" = true ]; then
    echo "--------------------------------------------------"
    echo "Saving thumbnails emulation..."
    /home/user/code/scripts/full_pipeline_scripts/run_thumbnail_saving.sh $EMULATION_DIR/$experiment/ $experiment "${methods_all[@]}"
    echo "Emulation complete."
    echo "--------------------------------------------------"
fi

rm -rf $EMULATION_DIR/$experiment/
echo "Done with $deployment: $experiment"
echo "############################################################################"