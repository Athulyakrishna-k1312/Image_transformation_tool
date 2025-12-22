import torch
from torchvision import transforms
from PIL import Image, ImageOps
from model import Generator  # from animegan2-pytorch repo

# Device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load model
def load_model(weight_path):
    model = Generator()
    model.load_state_dict(torch.load(weight_path, map_location=device))
    model.to(device)
    model.eval()
    return model

# Preprocess: resize but keep aspect ratio (pad instead of stretch)
def preprocess_image(image_path):
    image = Image.open(image_path).convert("RGB")
    image.thumbnail((512, 512), Image.Resampling.LANCZOS)  # keep ratio
    new_img = Image.new("RGB", (512, 512), (255, 255, 255))  # white padding
    new_img.paste(image, ((512 - image.width) // 2, (512 - image.height) // 2))

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])
    return transform(new_img).unsqueeze(0).to(device)

# Convert tensor → image
def tensor_to_image(tensor):
    tensor = tensor.squeeze(0).cpu()
    tensor = (tensor + 1) / 2  # back to [0,1]
    tensor = tensor.clamp(0, 1)
    return transforms.ToPILImage()(tensor)

# Cartoonize function (style selectable)
def animegan_cartoonize(input_path, output_path, style="face_paint_512_v2"):
    # Pretrained weights map
    weights = {
        "face_paint_512_v2": "weights/face_paint_512_v2.pt",
        "celeba_distill": "weights/celeba_distill.pt",
        "face_paint_512_v1": "weights/face_paint_512_v1.pt",
        
        "paprika": "weights/paprika.pt"
        

    }

    if style not in weights:
        raise ValueError(f"Unknown style: {style}. Choose from {list(weights.keys())}")

    model = load_model(weights[style])
    input_tensor = preprocess_image(input_path)

    with torch.no_grad():
        output_tensor = model(input_tensor)

    output_image = tensor_to_image(output_tensor)
    output_image.save(output_path)

    print(f"Cartoonized ({style}) saved at: {output_path}")
    return output_path



