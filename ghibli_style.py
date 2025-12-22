import onnxruntime as ort
import cv2
import numpy as np

# Load the ONNX model once
providers = ['CPUExecutionProvider']
model_path = "AnimeGANv3_Hayao_STYLE_36.onnx"
session = ort.InferenceSession(model_path, providers=providers)

# Preprocess image
def process_image(img, max_dimension=1024):
    h, w = img.shape[:2]
    if max(h, w) > max_dimension:
        scale = max_dimension / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    
    # Pad to multiple of 8
    h, w = img.shape[:2]
    new_h, new_w = h - h % 8, w - w % 8
    img = cv2.resize(img, (new_w, new_h))

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 127.5 - 1.0
    return np.expand_dims(img, axis=0), (h, w)

# Run inference
def ghibli_cartoonize(input_path, output_path):
    img0 = cv2.imread(input_path)
    if img0 is None:
        raise ValueError(f"Could not load image {input_path}")

    img, orig_size = process_image(img0)
    input_name = session.get_inputs()[0].name

    fake_img = session.run(None, {input_name: img})[0]
    images = (np.squeeze(fake_img) + 1.) / 2 * 255
    images = np.clip(images, 0, 255).astype(np.uint8)

    # Resize back
    output_image = cv2.resize(images, (orig_size[1], orig_size[0]))
    cv2.imwrite(output_path, cv2.cvtColor(output_image, cv2.COLOR_RGB2BGR))
    return output_path
