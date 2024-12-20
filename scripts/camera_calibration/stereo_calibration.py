import numpy as np
import cv2
import glob
import argparse
from tqdm import tqdm
import yaml
import os
from os.path import join

class StereoCalibration(object):
    def __init__(self, filepath, rows, columns, size_square, ransac=False, num_images=20, iterations=100):
        # termination criteria
        self.criteria = (cv2.TERM_CRITERIA_EPS +
                         cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.criteria_cal = (cv2.TERM_CRITERIA_EPS +
                             cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-5)
        self.rows = rows
        self.columns = columns
        self.size_square = size_square

        self.ransac = ransac
        self.ransac_images = num_images
        self.ransac_iterations = iterations
        
        # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
        self.objp = np.zeros((self.rows*self.columns, 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:self.rows, 0:self.columns].T.reshape(-1, 2)
        self.objp = self.objp*self.size_square

        # Arrays to store object points and image points from all the images.
        self.objpoints = []  # 3d point in real world space
        self.imgpoints_l = []  # 2d points in image plane.
        self.imgpoints_r = []  # 2d points in image plane.

        self.cal_path = filepath
        self.read_images(self.cal_path)

    def read_images(self, cal_path):
        print("Extracting chessboard corners...")
        print("Calibration path: ", cal_path)
        images_right = sorted(glob.glob(join(cal_path, 'camera_right_good/*.png')))
        images_left = sorted(glob.glob(join(cal_path, 'camera_left_good/*.png')))

        self.im_left = []
        self.im_right = []

        for i, fname in tqdm(enumerate(images_right)):
            gray_l = cv2.imread(images_left[i], cv2.IMREAD_GRAYSCALE)
            gray_r = cv2.imread(images_right[i], cv2.IMREAD_GRAYSCALE)

            self.img_shape = gray_l.shape[::-1]
            self.im_left.append(gray_l)
            self.im_right.append(gray_r)

            # Find the chess board corners
            ret_l, corners_l = cv2.findChessboardCorners(gray_l, (self.rows, self.columns), None, flags = cv2.CALIB_CB_FAST_CHECK)
            ret_r, corners_r = cv2.findChessboardCorners(gray_r, (self.rows, self.columns), None, flags = cv2.CALIB_CB_FAST_CHECK)

            if ret_l is True and ret_r is True:
                # If found, add object points, image points (after refining them)
                self.objpoints.append(self.objp)
                cv2.cornerSubPix(gray_l, corners_l, (11, 11), (-1, -1), self.criteria)
                self.imgpoints_l.append(corners_l)
                cv2.cornerSubPix(gray_r, corners_r, (11, 11), (-1, -1), self.criteria)
                self.imgpoints_r.append(corners_r)

        self.M1, self.d1 = self.calibrate_camera(self.objpoints, self.imgpoints_l, self.img_shape)
        self.M2, self.d2 = self.calibrate_camera(self.objpoints, self.imgpoints_r, self.img_shape)

    def calibrate_camera(self, objpoints, imgpoints, img_shape):

        print("-------------------------------------------------------------")
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
        best_iteration = 0
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
                best_iteration = i

        print(f"Best error: {min_error:.4f} at iteration {best_iteration} (mean: {np.mean(errors):.4f}, std: {np.std(errors):.4f})")
        return best_camera_matrix, best_dist_coeffs
    
    def compute_reprojection_error(self, objpoints, imgpoints, camera_matrix, dist_coeffs):
        mean_error = 0
        for i in range(len(objpoints)):
            # find the extrinsic parameters
            ret, rvecs, tvecs, _ = cv2.solvePnPRansac(objpoints[i], imgpoints[i], camera_matrix, dist_coeffs)
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs, tvecs, camera_matrix, dist_coeffs)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
            mean_error += error
        return mean_error/len(objpoints)
        
    def extract_intrinsics(self, file):
        with open(file, 'r') as f:
            intrinsics = yaml.safe_load(f)   
        return intrinsics["camera_matrix"]["data"], intrinsics["distortion_coefficients"]["data"]
    
    def set_intrinsics(self, which_cam, camera_matrix, dist_coeffs):
        if which_cam == "left":
            self.M1 = np.array(camera_matrix).reshape(3, 3)
            self.d1 = np.array(dist_coeffs)
        elif which_cam == "right":
            self.M2 = np.array(camera_matrix).reshape(3, 3)
            self.d2 = np.array(dist_coeffs)
    
    def stereo_calibrate(self):
        # flags = cv2.CALIB_FIX_INTRINSIC
        # flags |= cv2.CALIB_FIX_PRINCIPAL_POINT
        # flags = cv2.CALIB_USE_INTRINSIC_GUESS
        # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
        # flags |= cv2.CALIB_FIX_ASPECT_RATIO
        # flags |= cv2.CALIB_ZERO_TANGENT_DIST
        # flags |= cv2.CALIB_RATIONAL_MODEL
        # flags |= cv2.CALIB_SAME_FOCAL_LENGTH
        # flags |= cv2.CALIB_FIX_K3
        # flags |= cv2.CALIB_FIX_K4
        # flags |= cv2.CALIB_FIX_K5

        print("-------------------------------------------------------------")
        print("Starting stereo calibration...")

        stereocalib_criteria = (cv2.TERM_CRITERIA_MAX_ITER +
                                cv2.TERM_CRITERIA_EPS, 100, 1e-6)

        if not self.ransac:
            self.ransac_iterations = 1
            self.ransac_images = len(self.objpoints)

        min_error = np.inf
        errors = []
        best_model = None
        best_iteration = 0
        for i in tqdm(range(self.ransac_iterations)):
            if i == 0:
                print(f"First iteration is running with all the images (takes longer)")
                rnd_objpoints = np.array(self.objpoints)
                rnd_imgpoints_r = np.array(self.imgpoints_r)
                rnd_imgpoints_l = np.array(self.imgpoints_l)
            else:
                indices = np.random.choice(len(self.objpoints), self.ransac_images, replace=False)
                rnd_objpoints = np.array(self.objpoints)[indices]
                rnd_imgpoints_r = np.array(self.imgpoints_r)[indices]
                rnd_imgpoints_l = np.array(self.imgpoints_l)[indices]

            ret, M1, d1, M2, d2, R, T, E, F = cv2.stereoCalibrate(
                rnd_objpoints, rnd_imgpoints_l, rnd_imgpoints_r, 
                self.M1, self.d1, self.M2, self.d2, self.img_shape,
                criteria=stereocalib_criteria)#, flags=flags)
            
            error = self.compute_stereo_error(rnd_objpoints, self.imgpoints_l, self.imgpoints_r, M1, d1, M2, d2, R, T)
            errors.append(error)
            if error < min_error:
                min_error = error
                best_model = [M1, d1, M2, d2, R, T]
                best_iteration = i

        R1, R2, P1, P2, _, _, _ = cv2.stereoRectify(best_model[0], best_model[1], best_model[2], best_model[3], self.img_shape, best_model[4], best_model[5], flags=cv2.CALIB_ZERO_DISPARITY, alpha=0)   
        print(R1)
        self.camera_model = {
            'K1': best_model[0],
            'D1': best_model[1],
            'R1': R1,
            'P1': P1,
            'K2': best_model[2],
            'D2': best_model[3],
            'R2': R2,
            'P2': P2,
        }

        print(f"Best error: {min_error:.4f} at iteration {best_iteration} (mean: {np.mean(errors):.4f}, std: {np.std(errors):.4f})")
        return self.camera_model
    
    def compute_stereo_error(self, objpoints, imgpoints_l, imgpoints_r, M1, D1, M2, D2, R, T):
        mean_error = 0
        for i in range(len(objpoints)):
            R1, R2, P1, P2, _, _, _ = cv2.stereoRectify(M1, D1, M2, D2, self.img_shape, R, T, flags=cv2.CALIB_ZERO_DISPARITY, alpha=0)
            imgpoints_l_rect = cv2.undistortPoints(imgpoints_l[i], M1, D1, R=R1, P=P1)
            imgpoints_r_rect = cv2.undistortPoints(imgpoints_r[i], M2, D2, R=R2, P=P2)
            error = np.mean(np.abs(imgpoints_l_rect[:,:,1] - imgpoints_r_rect[:,:,1]))
            mean_error += error

        return mean_error/len(objpoints)
    
    def save_calibration(self, file):
        print("Saving calibration data...")
        output_model = {
            'K1': self.camera_model['K1'].ravel().tolist(),
            'D1': self.camera_model['D1'].ravel().tolist(),
            'R1': self.camera_model['R1'].ravel().tolist(),
            'P1': self.camera_model['P1'].ravel().tolist(),
            'K2': self.camera_model['K2'].ravel().tolist(),
            'D2': self.camera_model['D2'].ravel().tolist(),
            'R2': self.camera_model['R2'].ravel().tolist(),
            'P2': self.camera_model['P2'].ravel().tolist(),
        }
        with open(file, 'w') as f:
            yaml.dump(output_model, f, default_flow_style=None, sort_keys=False)
            print("Calibration data saved to stereo_calibration.yaml")
    
    def visualize_stereo_calibration(self):
        print("Visualizing stereo calibration...")
        mapx1, mapy1 = cv2.initUndistortRectifyMap(self.camera_model['K1'], self.camera_model['D1'], self.camera_model['R1'], self.camera_model['P1'], self.img_shape, cv2.CV_32FC1)
        mapx2, mapy2 = cv2.initUndistortRectifyMap(self.camera_model['K2'], self.camera_model['D2'], self.camera_model['R2'], self.camera_model['P2'], self.img_shape, cv2.CV_32FC1)

        for img_left, img_right in zip(self.im_left, self.im_right):
            img_left_rect = cv2.remap(img_left, mapx1, mapy1, cv2.INTER_LINEAR)
            img_right_rect = cv2.remap(img_right, mapx2, mapy2, cv2.INTER_LINEAR)
            stacked_img = np.hstack((img_left_rect, img_right_rect))
            stacked_img = cv2.resize(stacked_img, (0, 0), fx=0.5, fy=0.5)
            for i in range(0, stacked_img.shape[0], stacked_img.shape[0]//20):
                cv2.line(stacked_img, (0, i), (stacked_img.shape[1], i), (0, 255, 0), 1)
            cv2.imshow("Stereo calibration", stacked_img)
            if cv2.waitKey(0) == 27:  # Escape key
                cv2.destroyAllWindows()
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f','--file_path', help='(String) Filepath')
    parser.add_argument('-i','--intrinsics', help='(Bool) If want to use already calculated intrinsic parameters', action='store_true')
    parser.add_argument('-r','--ransac', help='(Bool) If want to use RANSAC to improve calibration', action='store_true')
    parser.add_argument('--images', help='Number of images for RANSAC', type=int, default=20)
    parser.add_argument('--iterations', help='Number of iterations for RANSAC', type=int, default=100)
    args = parser.parse_args()
    
    # Read stereo images
    # cal_data = StereoCalibration(args.file_path, rows=11, columns=8, size_square=0.06)
    cal_data = StereoCalibration(args.file_path, rows=11, columns=8, size_square=0.06, 
                                 ransac=args.ransac, num_images=args.images, iterations=args.iterations)
    
    # Fetch already calculated intrinsic parameters
    if args.intrinsics:
        print("Using already calculated intrinsic parameters")
        camera_left_calib_file = "scripts/data_calibration/11-09-2023_calibrationdata_camera1/manual_calib_file.yaml"
        camera_left_k, camera_left_d = cal_data.extract_intrinsics(camera_left_calib_file)
        cal_data.set_intrinsics("left", camera_left_k, camera_left_d)
        camera_right_calib_file = "scripts/data_calibration/11-09-2023_calibrationdata_camera2/manual_calib_file.yaml"
        camera_right_k, camera_right_d = cal_data.extract_intrinsics(camera_right_calib_file)
        cal_data.set_intrinsics("right", camera_right_k, camera_right_d)
    
    # Stereo calibration
    camera_model = cal_data.stereo_calibrate()
    cal_data.save_calibration(join(args.file_path, 'stereo_calibration.yaml'))
    cal_data.visualize_stereo_calibration()