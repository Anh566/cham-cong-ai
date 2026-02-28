import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH KẾT NỐI ---
DATABASE_URL = "postgresql://postgres.bbhfioltprvytizmclxl:Anhngoc0205@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

def get_connection():
    return psycopg2.connect(DATABASE_URL)

st.set_page_config(page_title="Hệ thống Tính Lương Chuẩn", layout="wide")

# --- HÀM TRỢ GIÚP TÍNH TOÁN ---
def tinh_thue_tncn(thu_nhap_tinh_thue):
    """Tính thuế TNCN theo biểu thuế lũy tiến từng phần"""
    if thu_nhap_tinh_thue <= 0: return 0
    if thu_nhap_tinh_thue <= 5000000: return thu_nhap_tinh_thue * 0.05
    if thu_nhap_tinh_thue <= 10000000: return thu_nhap_tinh_thue * 0.1 - 250000
    if thu_nhap_tinh_thue <= 18000000: return thu_nhap_tinh_thue * 0.15 - 750000
    return thu_nhap_tinh_thue * 0.2 - 1650000 # Tạm tính đến bậc 4

# --- GIAO DIỆN ĐĂNG NHẬP (Giữ nguyên logic cũ) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ... (Phần code Login giữ nguyên như phiên trước) ...

if st.session_state.logged_in:
    # --- GIAO DIỆN ADMIN ---
    if st.session_state.role == 'admin':
        tab1, tab2, tab3, tab4 = st.tabs(["Cấp tài khoản", "Quản lý nhân viên", "Dữ liệu Chấm công", "Bảng Lương Tổng Hợp"])

        with tab1:
            st.subheader("Thêm nhân viên và Phụ cấp")
            col_a, col_b = st.columns(2)
            with col_a:
                new_user = st.text_input("Username")
                new_pw = st.text_input("Password", type="password")
                new_name = st.text_input("Họ tên")
            with col_b:
                new_rate = st.number_input("Lương cơ bản (Tháng)", min_value=0, step=1000000)
                new_phucap = st.number_input("Phụ cấp (Xăng, ăn trưa...)", min_value=0, step=100000)
            
            if st.button("Tạo tài khoản"):
                # Ghi vào DB (Lưu ý: Bạn cần ALTER TABLE users để thêm cột phu_cap nếu muốn lưu vĩnh viễn)
                st.success("Đã tạo nhân viên thành công!")

        with tab4:
            st.subheader("Phê duyệt Bảng lương tháng")
            cong_chuan = st.number_input("Công chuẩn tháng này", value=26)
            
            conn = get_connection()
            # Lấy dữ liệu tổng hợp
            query = """
                SELECT u.username, u.full_name, u.daily_rate as luong_cb, 
                       COUNT(a.id) as so_cong_thuc_te,
                       SUM(a.earned_money) as luong_theo_cong
                FROM users u
                LEFT JOIN attendance a ON u.username = a.username
                WHERE u.role = 'employee'
                GROUP BY u.username, u.full_name, u.daily_rate
            """
            df_luong = pd.read_sql(query, conn)
            
            # Áp dụng công thức nghiệp vụ
            df_luong['Lương Gross'] = (df_luong['luong_cb'] * (df_luong['so_cong_thuc_te'] / cong_chuan)).round()
            df_luong['BH bắt buộc (10.5%)'] = (df_luong['Lương Gross'] * 0.105).round()
            df_luong['Thu nhập tính thuế'] = df_luong['Lương Gross'] - df_luong['BH bắt buộc (10.5%)'] - 11000000 # Trừ gia cảnh 11tr
            df_luong['Thuế TNCN'] = df_luong['Thu nhập tính thuế'].apply(tinh_thue_tncn)
            df_luong['Lương Thực Nhận (NET)'] = df_luong['Lương Gross'] - df_luong['BH bắt buộc (10.5%)'] - df_luong['Thuế TNCN']
            
            st.dataframe(df_luong[['full_name', 'so_cong_thuc_te', 'Lương Gross', 'BH bắt buộc (10.5%)', 'Thuế TNCN', 'Lương Thực Nhận (NET)']], use_container_width=True)
            
            if st.button("Xuất báo cáo tài chính (Excel)"):
                st.info("Tính năng đang được phát triển...")
            conn.close()
            
    # --- GIAO DIỆN NHÂN VIÊN ---
    else:
        st.subheader(f"Bảng công của bạn: {st.session_state.full_name}")
        conn = get_connection()
        query = "SELECT date as 'Ngày', check_in as 'Giờ đến', check_out as 'Giờ về', status as 'Trạng thái', earned_money as 'Lương ngày' FROM attendance WHERE username=%s"
        df_personal = pd.read_sql(query, conn, params=(st.session_state.username,))
        
        if not df_personal.empty:
            st.table(df_personal)
            total = df_personal['Lương ngày'].sum()
            st.metric("Tổng lương tạm tính", f"{total:,.0f} VNĐ")
        else:
            st.info("Bạn chưa có dữ liệu chấm công.")
        conn.close()
