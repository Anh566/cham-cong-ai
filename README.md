# HỆ THỐNG CHẤM CÔNG NHẬN DIỆN KHUÔN MẶT AI THỜI GIAN THỰC

> **Sinh viên thực hiện:** Đồng Vũ Ngọc Anh  
> **Trường:** Đại học Bách Khoa Hà Nội 

## 1. Giới thiệu (Introduction)
Hệ thống chấm công tự động sử dụng thiết bị thu thập hình ảnh **ESP32-CAM** và trạm xử lý trung tâm **MacBook Air M2**. Dự án ứng dụng các thuật toán **SOTA (State-of-the-Art)** trong lĩnh vực Thị giác máy tính để nhận diện danh tính và ngăn chặn các hành vi giả mạo bằng hình ảnh 2D.

## 2. Công nghệ sử dụng (Technology Stack)
* **AI Framework:** InsightFace (RetinaFace cho Detection, ArcFace cho Recognition).
* **Hardware:** ESP32-CAM (AI-Thinker), MacBook Air M2.
* **Algorithm Highlights:**
    * **ArcFace (Additive Angular Margin Loss):** Trích xuất vector đặc trưng 512 chiều trên mặt cầu đơn vị.
    * **In-Memory Augmentation:** Tăng cường dữ liệu trực tiếp trên RAM để tối ưu I/O.
    * **Anti-Spoofing:** Kiểm tra độ biến thiên Laplacian để phát hiện ảnh chụp giả mạo.

## 3. Kiến trúc hệ thống (System Architecture)
Hệ thống hoạt động theo mô hình Client-Server:
1. **ESP32-CAM:** Thu hình ảnh (VGA) và stream qua HTTP M-JPEG.
2. **MacBook M2:** Đọc luồng stream đa luồng (Multi-threading), tiền xử lý (CLAHE) và chạy suy luận AI.
3. **Database:** Lưu trữ vector đặc trưng dưới dạng nhị phân (.pkl) để so khớp tốc độ cao.

## 4. Hướng dẫn cài đặt (Setup)
1. Cài đặt thư viện: `pip install insightface onnxruntime-silicon opencv-python numpy`
2. Nạp code Arduino trong thư mục `CameraWebServer` cho ESP32-CAM.
3. Cập nhật IP của ESP32 vào file `recognition_webcam3_esp32.py`.
4. Chạy ứng dụng: file `recognition_webcam3_esp32.py` và nhận diện khuôn mặt 
5. Truy cập web chấm công bằng đường link: https://cham-cong-ai.streamlit.app/


---

