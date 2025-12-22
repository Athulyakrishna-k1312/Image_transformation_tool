import cv2
import numpy as np

def cartoonize_image(img_path):
    # Read image from file path
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Could not load image from {img_path}")

    # 1. Resize for consistency (optional, keep high res)
    #img = cv2.resize(img, (800, 800))  # you can change size

    # 2. Smooth the image (remove noise)
    img_color = cv2.bilateralFilter(img, d=9, sigmaColor=200, sigmaSpace=200)

    # 3. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 4. Median blur for smooth edges
    gray_blur = cv2.medianBlur(gray, 7)

    # 5. Detect edges using adaptive threshold
    edges = cv2.adaptiveThreshold(
        gray_blur, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=9,
        C=2
    )

    # 6. Convert edges to color
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # 7. Combine edges with the smoothed image
    cartoon = cv2.bitwise_and(img_color, edges_colored)

    return cartoon
