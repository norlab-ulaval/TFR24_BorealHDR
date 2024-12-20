import pandas as pd
import cv2 
import os
from pathlib import Path
import argparse
import threading
import numpy as np


########### PARAMS ############

parser = argparse.ArgumentParser(description="Emulate from a bracketing sequence")
parser.add_argument("-i", "--input_folder", help="Folder with emulated images", required=True)
parser.add_argument("-x", "--experiment", help="Experiment name", required=True)
parser.add_argument("-m", "--methods",type=str, nargs='+', help="Experiment name", required=True)
args = parser.parse_args()

FPS = 22/6
VIDEO_NAME = "emulation_video"
SCALE = 0.2

EXPERIMENT = args.experiment
AE_METRICS = args.methods
INPUT_FOLDER = Path(args.input_folder)
BASE_PATH = Path(__file__).absolute().parents[2]
SAVE_PATH = BASE_PATH / "results" / "stereo" / EXPERIMENT

###############################


def save_exposure_times(ae_folder, metric_name):
    data = pd.read_csv(ae_folder / "times_images_left.txt", names=["timestamp", "exposure_time"], sep=" ")
    data.to_csv(SAVE_PATH / metric_name / "exposure_times_left.csv", index=False, header=False)
    data = pd.read_csv(ae_folder / "times_images_right.txt", names=["timestamp", "exposure_time"], sep=" ")
    data.to_csv(SAVE_PATH / metric_name / "exposure_times_right.csv", index=False, header=False)


def make_video_preview(ae_folder,  metric_name):
    images_left = [img for img in sorted(os.listdir(ae_folder / "images_left")) if img.endswith(".png")]  
    images_right = [img for img in sorted(os.listdir(ae_folder / "images_right")) if img.endswith(".png")]  
    frame_left = cv2.imread(os.path.join(ae_folder / "images_left", images_left[0]), cv2.IMREAD_GRAYSCALE)
    height, width = frame_left.shape
    final_shape = (int(2*width*SCALE), int(height*SCALE))

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    tmp_video_file = str(SAVE_PATH / metric_name / f"{EXPERIMENT}_{metric_name}.avi")
    final_video_file = str(SAVE_PATH / metric_name / f"{EXPERIMENT}_{metric_name}.mp4")
    video = cv2.VideoWriter(tmp_video_file, fourcc, FPS, final_shape, isColor=False)

    for image_left, image_right in zip(images_left,images_right):
        img_left = cv2.imread(os.path.join(ae_folder / "images_left", image_left), cv2.IMREAD_ANYDEPTH)
        img_right = cv2.imread(os.path.join(ae_folder / "images_right", image_right), cv2.IMREAD_ANYDEPTH)
        img_left = (img_left/16.0).astype('uint8')
        img_right = (img_right/16.0).astype('uint8')
        img = np.hstack((img_left, img_right))
        img_down = cv2.resize(img, final_shape, interpolation=cv2.INTER_AREA)
        video.write(img_down)    
    
    cv2.destroyAllWindows()
    video.release()
    os.system(f"ffmpeg -y -i \"{tmp_video_file}\" -vcodec libx265 \"{final_video_file}\" -nostats -loglevel 0")
    os.system(f"rm \"{tmp_video_file}\"")

def main():

    exposure_graph = INPUT_FOLDER / "exposure_times.png"
    cv2.imwrite(os.path.join(str(SAVE_PATH), "exposure_times.png"), cv2.imread(str(exposure_graph)))
    
    # Run the experiments in parallel
    threads = []
    for metric in AE_METRICS:
        if not os.path.isdir(SAVE_PATH / metric): os.makedirs(SAVE_PATH / metric)
        ae_folder = INPUT_FOLDER / f"ae-{metric}"
        t = threading.Thread(target=save_exposure_times, args=(ae_folder, metric,))
        threads.append(t)
        t.start()
        t = threading.Thread(target=make_video_preview, args=(ae_folder, metric,))
        threads.append(t)
        t.start()

    print("All threads started")
    for index, thread in enumerate(threads):
        thread.join()
        # print(f"Thread {index} done")


if __name__ == "__main__":
    main()