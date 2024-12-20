import cv2
import numpy as np
import os
import argparse

# List of images in the directory

def select_images(images_path, bits, bayer, images_to_use):
    # Create the good folder if it does not exist
    images_left_path = os.listdir(os.path.join(images_path, 'camera_left'))
    images_right_path = os.listdir(os.path.join(images_path, 'camera_right'))

    good_folder_left = os.path.join(images_path, 'camera_left_good')
    good_folder_right = os.path.join(images_path, 'camera_right_good')
    if not os.path.exists(good_folder_left) or not os.path.exists(good_folder_right):
        os.makedirs(good_folder_left)
        os.makedirs(good_folder_right)

    print("----------------------------------------------------------------------------------")
    print("To save the image press 's' key. To skip press any other key")
    print("----------------------------------------------------------------------------------")

    # List of images to be used for calibration
    for idx, (img_left_file, img_right_file) in enumerate(zip(sorted(images_left_path), sorted(images_right_path))):
        if img_left_file != img_right_file:
            print(f'Images do not match: {img_left_file} != {img_right_file}')
            continue
        
        if idx % images_to_use != 0:
            continue
        
        # Read the image
        img_left = cv2.imread(os.path.join(images_path, 'camera_left', img_left_file), cv2.IMREAD_ANYDEPTH)
        img_right = cv2.imread(os.path.join(images_path, 'camera_right', img_right_file), cv2.IMREAD_ANYDEPTH)
        
        # Convert to 8 bits
        if bits == 12:
            img_left = (img_left/16.0).astype(np.uint8)
            img_right = (img_right/16.0).astype(np.uint8)
        if bayer:
            img_left = cv2.cvtColor(img_left, cv2.COLOR_BAYER_RG2GRAY)
            img_right = cv2.cvtColor(img_right, cv2.COLOR_BAYER_RG2GRAY)
        
        # Display the images side-by-side and resize of 50%
        img = np.concatenate((img_left, img_right), axis=1)
        img = cv2.resize(img, (0,0), fx=0.4, fy=0.4)
        cv2.imshow(f"Idx: {idx} - {img_left_file}", img)

        # Wait for key press
        key = cv2.waitKey(0)

        # Check if 's' key is pressed
        if key == ord('s'):
            # Save the image to the good folder
            cv2.imwrite(os.path.join(good_folder_left, img_left_file), img_left)
            cv2.imwrite(os.path.join(good_folder_right, img_right_file), img_right)

        # Close the image window
        cv2.destroyAllWindows()

def main():
    ########### PARAMS ############ 
    parser = argparse.ArgumentParser(description='Monocular calibration')
    parser.add_argument('-b','--bits', type=int, default=8, help='Number of bits of the images')
    parser.add_argument('--bayer', action='store_true', help='Need to debayer the images')
    parser.add_argument('-i','--images_path', type=str, help='Path to the left and right images folder')
    parser.add_argument('--fps', type=int, default=10, help='Number of frames per second')

    INPUT_BITS = parser.parse_args().bits
    BAYER = parser.parse_args().bayer
    IMAGES_DIR = parser.parse_args().images_path

    FPS = parser.parse_args().fps
    NUMBER_OF_IMAGES_PER_SECOND_TO_VISUALIZE = 0.7
    percentage_images_to_use = int((1/NUMBER_OF_IMAGES_PER_SECOND_TO_VISUALIZE)*FPS)
    ###############################

    select_images(IMAGES_DIR, INPUT_BITS, BAYER, percentage_images_to_use)

if __name__ == '__main__':
    main()