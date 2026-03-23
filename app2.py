import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import os

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
    return thu_nhap_tinh_thue * 0.2 - 1650000

# --- KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # GIAO DIỆN ĐĂNG NHẬP
    st.title("🔐 Đăng nhập hệ thống")
    with st.form("login_form"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Đăng nhập"):
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT full_name, role FROM users WHERE username=%s AND password=%s", (user, pw))
                res = cur.fetchone()
                if res:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.full_name = res[0]
                    st.session_state.role = res[1]
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu")
                conn.close()
            except Exception as e:
                st.error(f"Lỗi kết nối Database: {e}")
else:
    # GIAO DIỆN SAU KHI ĐĂNG NHẬP
    st.sidebar.title(f"Chào, {st.session_state.full_name}")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()

    # --- GIAO DIỆN ADMIN ---
    if st.session_state.role == 'admin':
        tab1, tab2, tab3, tab4 = st.tabs(["Cấp tài khoản", "Quản lý nhân viên", "Dữ liệu Chấm công", "Bảng Lương Tổng Hợp"])

        with tab1:
            st.subheader("➕ Cấp tài khoản nhân viên mới")
            with st.form("create_user_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    new_user = st.text_input("Mã nhân viên (Username) *")
                    new_pw = st.text_input("Mật khẩu mới *", type="password")
                    new_name = st.text_input("Họ tên đầy đủ *")
                    danh_sach_phong = ["IT - Kỹ thuật", "Hành chính - Nhân sự", "Kế toán", "Marketing", "Vận hành", "Khác"]
                    new_phongban = st.selectbox("Phòng ban", danh_sach_phong)
                with col_b:
                    new_rate = st.number_input("Lương cơ bản (Tháng)", min_value=0, step=1000000)
                    new_phucap = st.number_input("Phụ cấp (Xăng, ăn...)", min_value=0, step=100000)
                
                if st.form_submit_button("Tạo tài khoản"):
                    if not new_user or not new_pw or not new_name:
                        st.warning("⚠️ Vui lòng điền đầy đủ thông tin bắt buộc!")
                    else:
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("SELECT username FROM users WHERE username = %s", (new_user,))
                            if cur.fetchone():
                                st.error(f"❌ Mã nhân viên '{new_user}' đã tồn tại!")
                            else:
                                cur.execute("INSERT INTO users (username, password, full_name, role, daily_rate, phu_cap, phong_ban) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                            (new_user, new_pw, new_name, 'employee', new_rate, new_phucap, new_phongban))
                                conn.commit()
                                st.success(f"✅ Đã tạo thành công tài khoản cho {new_name}")
                            conn.close()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")

        with tab2:
            st.subheader("Danh sách nhân sự và Quản lý")
            conn = get_connection()
            df_u = pd.read_sql("SELECT username, password, full_name, phong_ban, daily_rate, phu_cap FROM users WHERE role='employee'", conn)
            
            for index, row in df_u.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 2])
                col1.write(f"**@{row['username']}**")
                col2.code(row['password']) 
                col3.write(f"{row['full_name']} ({row['phong_ban']})")
                col4.write(f"{row['daily_rate']:,}đ")
                
                with col5:
                    btn_edit, btn_del = st.columns(2)
                    if btn_del.button("Xóa", key=f"del_{row['username']}"):
                        cur = conn.cursor()
                        cur.execute("DELETE FROM attendance WHERE username=%s", (row['username'],))
                        cur.execute("DELETE FROM users WHERE username=%s", (row['username'],))
                        conn.commit()
                        st.rerun()

                    edit_toggle = btn_edit.toggle("Sửa", key=f"tg_{row['username']}")

                if edit_toggle:
                    with st.container(border=True):
                        with st.form(key=f"form_edit_{row['username']}"):
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.text_input("Mã nhân viên", value=row['username'], disabled=True)
                                edit_pw = st.text_input("Mật khẩu mới", value=row['password'])
                            with c2:
                                edit_name = st.text_input("Họ tên", value=row['full_name'])
                                danh_sach_phong = ["IT - Kỹ thuật", "Hành chính - Nhân sự", "Kế toán", "Marketing", "Vận hành", "Khác"]
                                idx_phong = danh_sach_phong.index(row['phong_ban']) if row['phong_ban'] in danh_sach_phong else 5
                                edit_phong = st.selectbox("Phòng ban", danh_sach_phong, index=idx_phong, key=f"phong_{row['username']}")
                            with c3:
                                edit_rate = st.number_input("Lương cơ bản", value=int(row['daily_rate']), step=500000)
                                edit_phucap = st.number_input("Phụ cấp", value=int(row['phu_cap']), step=100000)
                            
                            if st.form_submit_button("💾 Lưu thay đổi"):
                                try:
                                    cur = conn.cursor()
                                    cur.execute("""
                                        UPDATE users 
                                        SET password=%s, full_name=%s, phong_ban=%s, daily_rate=%s, phu_cap=%s 
                                        WHERE username=%s
                                    """, (edit_pw, edit_name, edit_phong, edit_rate, edit_phucap, row['username']))
                                    conn.commit()
                                    st.cache_data.clear() # XÓA CACHE ĐỂ ĐỒNG BỘ DỮ LIỆU
                                    st.success("Cập nhật thành công!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Lỗi: {e}")
            conn.close()
            
        with tab3:
            st.subheader("Lịch sử chấm công toàn công ty")
            conn = get_connection()
            query_tab3 = """
                SELECT a.date as "Ngày", u.full_name as "Họ tên", a.check_in as "Giờ đến", 
                       a.check_out as "Giờ về", a.status as "Trạng thái", a.earned_money as "Tiền công ngày"
                FROM attendance a
                LEFT JOIN users u ON a.username = u.username
                ORDER BY a.date DESC, a.check_in DESC
            """
            df_attendance_all = pd.read_sql(query_tab3, conn)
            if not df_attendance_all.empty:
                st.dataframe(df_attendance_all.style.format({"Tiền công ngày": "{:,.0f}"}), use_container_width=True)
            conn.close()    

        with tab4:
            st.subheader("Phê duyệt Bảng lương tháng")
            cong_chuan = st.number_input("Công chuẩn tháng này", value=26)
            conn = get_connection()
            query = """
                SELECT u.username, u.full_name, u.daily_rate as luong_cb, u.phu_cap,
                       COUNT(a.id) as so_cong_thuc_te, SUM(a.earned_money) as luong_theo_cong
                FROM users u
                LEFT JOIN attendance a ON u.username = a.username
                WHERE u.role = 'employee'
                GROUP BY u.username, u.full_name, u.daily_rate, u.phu_cap
            """
            df_luong = pd.read_sql(query, conn)
            df_luong['Lương Gross'] = (df_luong['luong_cb'] * (df_luong['so_cong_thuc_te'] / cong_chuan) + df_luong['phu_cap']).round()
            df_luong['BHXH (10.5%)'] = (df_luong['Lương Gross'] * 0.105).round()
            df_luong['Thu nhập tính thuế'] = df_luong['Lương Gross'] - df_luong['BHXH (10.5%)'] - 11000000
            df_luong['Thuế TNCN'] = df_luong['Thu nhập tính thuế'].apply(tinh_thue_tncn)
            df_luong['NET Thực Nhận'] = df_luong['Lương Gross'] - df_luong['BHXH (10.5%)'] - df_luong['Thuế TNCN']
            st.dataframe(df_luong[['full_name', 'so_cong_thuc_te', 'NET Thực Nhận']].style.format({"NET Thực Nhận": "{:,.0f}"}), use_container_width=True)
            conn.close()

    # --- GIAO DIỆN NHÂN VIÊN ---
    elif st.session_state.role == 'employee':
        tab_info, tab_cong = st.tabs(["👤 Thông tin cá nhân", "📅 Bảng chấm công"])
        
        with tab_info:
            st.subheader("Hồ sơ Nhân viên")
            conn = get_connection()
            cur = conn.cursor()
            # SỬA LỖI: Lấy thêm cột phong_ban từ Database
            cur.execute("SELECT username, full_name, daily_rate, phu_cap, phong_ban FROM users WHERE username=%s", (st.session_state.username,))
            user_info = cur.fetchone()
            conn.close()
            
            if user_info:
                col_img, col_text = st.columns([1, 2])
                with col_img:
                    img_path = f"raw_image/{st.session_state.username}/{st.session_state.username}_0.jpg"
                    if os.path.exists(img_path):
                        st.image(img_path, width=200)
                    else:
                        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=200)
                
                with col_text:
                    st.markdown(f"**Họ và tên:** {user_info[1]}")
                    st.markdown(f"**Mã nhân viên:** {user_info[0]}")
                    st.markdown(f"**Chức vụ:** Nhân viên")
                    # SỬA LỖI: Hiển thị phòng ban động từ DB
                    st.markdown(f"**Phòng ban:** {user_info[4] if user_info[4] else 'Chưa cập nhật'}") 
                    st.markdown(f"**Mức lương cơ bản:** {user_info[2]:,.0f} VNĐ/Tháng")
                    st.markdown(f"**Phụ cấp cố định:** {user_info[3]:,.0f} VNĐ/Tháng")

        with tab_cong:
            st.subheader(f"Bảng công của bạn tháng này")
            conn = get_connection()
            query = "SELECT date, check_in, check_out, status, earned_money FROM attendance WHERE username=%s"
            df_personal = pd.read_sql(query, conn, params=(st.session_state.username,))
            if not df_personal.empty:
                st.table(df_personal.style.format({"earned_money": "{:,.0f}"}))
                st.metric("Tổng thu nhập tạm tính", f"{df_personal['earned_money'].sum():,.0f} VNĐ")
            conn.close()
