# 🎨 AI-based Image Transformation Platform
  
It is a web-based image transformation platform that allows users to convert images into **Cartoon**, **Pencil Sketch**, and **Anime-style AI effects**, with additional features like games, watermark control, subscriptions, and an admin dashboard.

---

## 📌 Project Overview

The platform allows users to upload an image and apply different artistic transformations using **OpenCV and AI techniques**.  
To encourage user engagement, a **mini catch game** is integrated that gives users a chance to download images **without watermark**.  
A **subscription-based model** is also implemented for unlimited downloads.

An **Admin Dashboard** is included to manage users, subscriptions, payments, and system analytics.

---

## 🛠️ Technologies I Used

- **Flask** – Web framework for the application  
- **MySQL** – Database for storing user data, image details, and subscriptions  
- **Razorpay API (Test Mode)** – Online payment integration  
- **Python & OpenCV** – Image processing using bilateral filtering and edge detection  

---

## ⚙️ How It Works

- Upload any photo  
- Convert it into:
  - Cartoon effect  
  - Pencil sketch (OpenCV)  
  - Anime-style AI model  
- Download the output:
  - With watermark **OR**
  - Play a **catch game** 🎮 to unlock a **watermark-free download**  
    - Limited to **5 attempts per day**
- Subscribe for **unlimited downloads**:
  - Daily plan  
  - Monthly plan  
  - Yearly plan 💳  

---

## Admin Dashboard

The Admin Panel provides full control over the platform, including:

- User management & subscription records  
- Image conversion history  
- Payment logs & transaction details  
- Subscription usage limits  
- Dashboard analytics and system controls 📊  

---
![Admin Dashboard](screenshots/admin_dashboard.png)




