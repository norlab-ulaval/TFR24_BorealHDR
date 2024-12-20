import numpy as np
import cv2
import glob
import argparse
from tqdm import tqdm
import yaml
from os.path import join

class MonocularCalibration(object):
    def __init__(self, filepath, rows, columns, size_square, ransac=False, num_images=20, iterations=100, visualize=False):
        # termination criteria
        self.criteria = (cv2.TERM_CRITERIA_EPS +
                         cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.criteria_cal = (cv2.TERM_CRITERIA_EPS +
                             cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-5)
        self.rows = rows
        self.columns = columns
        self.size_square = size_square
        self.visualize = visualize

        self.ransac = ransac
        self.ransac_images = num_images
        self.ransac_iterations = iterations
        
        # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
        self.objp = np.zeros((self.rows*self.columns, 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:self.rows, 0:self.columns].T.reshape(-1, 2)
        self.objp = self.objp*self.size_square

        # Arrays to store object points and image points from all the images.
        self.objpoints = []  # 3d point in real world space
        self.imgpoints = []  # 2d points in image plane.

        self.cal_path = filepath
        self.read_images(self.cal_path)

    def read_images(self, cal_path):
        print("Extracting chessboard corners...")
        print("Calibration path: ", cal_path)
        images = sorted(glob.glob(cal_path + '/*.png'))

        self.im = []

        for i, fname in tqdm(enumerate(images)):
            gray = cv2.imread(images[i], cv2.IMREAD_GRAYSCALE)

            self.img_shape = gray.shape[::-1]
            self.im.append(gray)

            # Find the chess board corners
            ret, corners = cv2.findChessboardCorners(gray, (self.rows, self.columns), None, flags = cv2.CALIB_CB_FAST_CHECK)

            if ret is True:
                # If found, add object points, image points (after refining them)
                self.objpoints.append(self.objp)
                cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
                self.imgpoints.append(corners)

                # Draw and display the corners
                if self.visualize:
                    cv2.drawChessboardCorners(gray, (self.rows, self.columns), corners, ret)
                    resized_img = cv2.resize(gray, (0, 0), fx=0.75, fy=0.75)
                    cv2.imshow(fname + ' Resized', resized_img)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()


        self.M, self.d, self.reprojection_error = self.calibrate_camera(self.objpoints, self.imgpoints, self.img_shape)

    def calibrate_camera(self, objpoints, imgpoints, img_shape):

        print(f"Starting intrinsics calibration")
        
        if not self.ransac:
            self.ransac_iterations = 1
            self.ransac_images = len(objpoints)

        if len(objpoints) < self.ransac_images:
            raise ValueError(f"Number of images is less than the required number of images: {self.ransac_images}")
        
        min_error = np.inf
        errors = []
        best_camera_matrix = None
        best_dist_coeffs = None
        for i in tqdm(range(self.ransac_iterations)):
            if i == 0:
                print(f"First iteration is running with all the images (takes longer)")
                rnd_objpoints = np.array(objpoints)
                rnd_imgpoints = np.array(imgpoints)
            else:
                indices = np.random.choice(len(objpoints), self.ransac_images, replace=False)
                rnd_objpoints = np.array(objpoints)[indices]
                rnd_imgpoints = np.array(imgpoints)[indices]

            # Calibrate the camera
            _, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(rnd_objpoints, rnd_imgpoints, img_shape, None, None)
            ret = self.compute_reprojection_error(objpoints, imgpoints, camera_matrix, dist_coeffs)
            errors.append(ret)
            if ret < min_error:
                min_error = ret
                best_camera_matrix= camera_matrix
                best_dist_coeffs = dist_coeffs

        print(f"Best error: {min_error:.4f} (mean: {np.mean(errors):.4f}, std: {np.std(errors):.4f})")
        return best_camera_matrix, best_dist_coeffs, min_error
    
    def compute_reprojection_error(self, objpoints, imgpoints, camera_matrix, dist_coeffs):
        mean_error = 0
        for i in range(len(objpoints)):
            # find the extrinsic parameters
            ret, rvecs, tvecs, _ = cv2.solvePnPRansac(objpoints[i], imgpoints[i], camera_matrix, dist_coeffs)
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs, tvecs, camera_matrix, dist_coeffs)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
            mean_error += error
        return mean_error/len(objpoints)

    def save_calibration(self, path, mtx, dist, reprojection_error):
        calib_dic = {
            "reprojection_error": reprojection_error,
            "image_width": self.img_shape[0],
            "image_heigh": self.img_shape[1],
            "camera_matrix": {
                "rows": 3,
                "cols": 3,
                "data": mtx.ravel().tolist(),
            },
            "distortion_coefficients": {
                "rows": 1,
                "cols": 5,
                "data": dist.ravel().tolist(),
            }
        }
        
        with open(path, 'w') as file:
            yaml.dump(calib_dic, file, default_flow_style=None, sort_keys=False)
            print("Calibration data saved to monocular_calibration.yaml")
        return

if __name__ == '__main__':
    ########### PARAMS ############ 
    parser = argparse.ArgumentParser(description='Monocular calibration')
    parser.add_argument('-i','--images_path', type=str, help='Path to the images folder')
    parser.add_argument('-r','--ransac', help='(Bool) If want to use RANSAC to improve calibration', action='store_true')
    parser.add_argument('--images', help='Number of images for RANSAC', type=int, default=20)
    parser.add_argument('--iterations', help='Number of iterations for RANSAC', type=int, default=100)
    parser.add_argument('-v','--visualize', action='store_true', help='Visualize the chessboard')
    args = parser.parse_args()
    ###############################
    
    cal_data = MonocularCalibration(args.images_path, rows=11, columns=8, size_square=0.06, 
                                 ransac=args.ransac, num_images=args.images, iterations=args.iterations, visualize=args.visualize)
    
    cal_data.save_calibration(join(args.images_path, 'monocular_calibration.yaml'), cal_data.M, cal_data.d, cal_data.reprojection_error)