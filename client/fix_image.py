from PIL import Image
import os

# Đường dẫn file ảnh lỗi
img_path = "./client/images/Face/admin.jpg"
# Đường dẫn file ảnh mới sau khi sửa
save_path = "./client/images/Face/admin_fixed.jpg"

if os.path.exists(img_path):
    try:
        # 1. Mở ảnh bằng thư viện Pillow (Xử lý định dạng tốt hơn OpenCV)
        img = Image.open(img_path)
        
        # 2. In thông tin ảnh cũ để kiểm tra
        print(f"Ảnh gốc: {img.format}, Mode: {img.mode}, Size: {img.size}")
        
        # 3. Ép chuyển về hệ màu RGB chuẩn (Loại bỏ Alpha, CMYK, Grayscale lạ)
        img = img.convert('RGB')
        
        # 4. Lưu lại đè lên file cũ hoặc ra file mới (Chất lượng cao nhất)
        img.save(save_path, "JPEG", quality=100)
        
        print(f"✅ Đã convert thành công! File mới tại: {save_path}")
        print("Bây giờ bạn hãy xóa 'admin.jpg' cũ đi và đổi tên 'admin_fixed.jpg' thành 'admin.jpg'")
        
    except Exception as e:
        print(f"❌ Lỗi khi xử lý: {e}")
else:
    print(f"❌ Không tìm thấy file {img_path}. Hãy chắc chắn bạn đã để ảnh vào thư mục 'images'")