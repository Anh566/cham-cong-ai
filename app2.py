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
            st.subheader("Thêm nhân viên và Phụ cấp")
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
            
            if st.button("Tạo tài khoản"):
                # 1. Kiểm tra xem Admin có nhập thiếu trường bắt buộc không
                if not new_user or not new_pw or not new_name:
                    st.warning("⚠️ Vui lòng điền đầy đủ Mã nhân viên, Mật khẩu và Họ tên!")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        
                        # 2. KIỂM TRA TRÙNG LẶP MÃ NHÂN VIÊN
                        cur.execute("SELECT username FROM users WHERE username = %s", (new_user,))
                        existing_user = cur.fetchone()
                        
                        if existing_user:
                            # Nếu tìm thấy người đã dùng mã này -> Báo lỗi và dừng lại
                            st.error(f"❌ LỖI: Mã nhân viên '{new_user}' đã tồn tại trong hệ thống! Vui lòng nhập một mã khác.")
                        else:
                            # 3. Nếu mã hợp lệ (chưa ai dùng) -> Tiến hành lưu vào Database
                            cur.execute("INSERT INTO users (username, password, full_name, role, daily_rate, phu_cap, phong_ban) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (new_user, new_pw, new_name, 'employee', new_rate, new_phucap, new_phongban))
                            conn.commit()
                            st.success(f"✅ Đã tạo thành công tài khoản cho {new_name} - Phòng {new_phongban}")
                            
                        conn.close()
                    except Exception as e:
                        st.error(f"Lỗi hệ thống: {e}")

        with tab2:
            st.subheader("Danh sách nhân sự và Quản lý")
            conn = get_connection()
            # Lấy toàn bộ thông tin cần thiết
            df_u = pd.read_sql("SELECT username, password, full_name, phong_ban, daily_rate, phu_cap FROM users WHERE role='employee'", conn)
            
            for index, row in df_u.iterrows():
                # Dành không gian cho nút Sửa và Xóa
                col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 2])
                
                col1.write(f"**@{row['username']}**")
                col2.code(row['password']) 
                col3.write(f"{row['full_name']} ({row['phong_ban']})")
                col4.write(f"{row['daily_rate']:,}đ")
                
                # Gom 2 nút Sửa và Xóa vào cùng 1 cột cho gọn
                with col5:
                    btn_edit, btn_del = st.columns(2)
                    
                    # 1. TÍNH NĂNG XÓA
                    if btn_del.button("Xóa", key=f"del_{row['username']}"):
                        try:
                            cur = conn.cursor()
                            cur.execute("DELETE FROM attendance WHERE username=%s", (row['username'],))
                            cur.execute("DELETE FROM users WHERE username=%s", (row['username'],))
                            conn.commit()
                            st.warning(f"Đã xóa tài khoản {row['username']}")
                            st.rerun() 
                        except Exception as e:
                            st.error(f"Lỗi khi xóa: {e}")

                    # 2. TÍNH NĂNG SỬA TÀI KHOẢN (Hiển thị form)
                    edit_toggle = btn_edit.toggle("Sửa", key=f"tg_{row['username']}")

                # Nếu Admin bật nút Sửa, hiện ra Form cập nhật ngay bên dưới dòng đó
                if edit_toggle:
                    with st.container(border=True):
                        st.markdown(f"**Cập nhật thông tin cho:** `{row['username']}`")
                        with st.form(key=f"form_edit_{row['username']}"):
                            c1, c2, c3 = st.columns(3)
                            
                            with c1:
                                # Ô username bị khóa (disabled=True)
                                st.text_input("Mã nhân viên (Không thể sửa)", value=row['username'], disabled=True)
                                edit_pw = st.text_input("Mật khẩu mới", value=row['password'])
                            with c2:
                                edit_name = st.text_input("Họ tên", value=row['full_name'])
                                danh_sach_phong = ["IT - Kỹ thuật", "Hành chính - Nhân sự", "Kế toán", "Marketing", "Vận hành", "Khác"]
                                # Chọn lại phòng ban, lấy index cũ nếu có
                                idx_phong = danh_sach_phong.index(row['phong_ban']) if row['phong_ban'] in danh_sach_phong else 5
                                edit_phong = st.selectbox("Phòng ban", danh_sach_phong, index=idx_phong, key=f"phong_{row['username']}")
                            with c3:
                                edit_rate = st.number_input("Lương cơ bản", value=int(row['daily_rate']), step=500000)
                                edit_phucap = st.number_input("Phụ cấp", value=int(row['phu_cap']), step=100000)
                            
                            submit_edit = st.form_submit_button("💾 Lưu thay đổi")
                            if submit_edit:
                                try:
                                    cur = conn.cursor()
                                    cur.execute("""
                                        UPDATE users 
                                        SET password=%s, full_name=%s, phong_ban=%s, daily_rate=%s, phu_cap=%s 
                                        WHERE username=%s
                                    """, (edit_pw, edit_name, edit_phong, edit_rate, edit_phucap, row['username']))
                                    conn.commit()
                                    st.success("Đã cập nhật thành công! Đang tải lại...")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Lỗi cập nhật: {e}")
            conn.close()
            
        with tab3:
            st.subheader("Lịch sử chấm công toàn công ty")
            conn = get_connection()
            
            # Lấy dữ liệu chấm công của tất cả mọi người, ghép với tên thật từ bảng users
            query_tab3 = """
                SELECT a.date as "Ngày", 
                       u.full_name as "Họ tên", 
                       a.check_in as "Giờ đến", 
                       a.check_out as "Giờ về", 
                       a.status as "Trạng thái", 
                       a.earned_money as "Tiền công ngày"
                FROM attendance a
                LEFT JOIN users u ON a.username = u.username
                ORDER BY a.date DESC, a.check_in DESC
            """
            df_attendance_all = pd.read_sql(query_tab3, conn)
            
            if not df_attendance_all.empty:
                # Ép định dạng tiền tệ cho cột Tiền công ngày để dễ nhìn
                st.dataframe(
                    df_attendance_all.style.format({"Tiền công ngày": "{:,.0f}"}),
                    use_container_width=True,
                    height=400 # Giới hạn chiều cao bảng để cuộn cho đẹp
                )
                
                # Nút tải dữ liệu thô (tùy chọn thêm cho Admin)
                csv = df_attendance_all.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải nhật ký chấm công (CSV)",
                    data=csv,
                    file_name=f"nhat_ky_cham_cong_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                )
            else:
                st.info("Chưa có dữ liệu chấm công nào trong hệ thống.")
                
            conn.close()    

        with tab4:
            st.subheader("Phê duyệt Bảng lương tháng")
            cong_chuan = st.number_input("Công chuẩn tháng này", value=26)
            
            conn = get_connection()
            query = """
                SELECT u.username, u.full_name, u.daily_rate as luong_cb, u.phu_cap,
                       COUNT(a.id) as so_cong_thuc_te,
                       SUM(a.earned_money) as luong_theo_cong
                FROM users u
                LEFT JOIN attendance a ON u.username = a.username
                WHERE u.role = 'employee'
                GROUP BY u.username, u.full_name, u.daily_rate, u.phu_cap
            """
            df_luong = pd.read_sql(query, conn)
            
            # Tính toán nghiệp vụ
            # Lương Gross = (Lương CB * (Số công / Công chuẩn)) + Phụ cấp
            df_luong['Lương Gross'] = (df_luong['luong_cb'] * (df_luong['so_cong_thuc_te'] / cong_chuan) + df_luong['phu_cap']).round()
            df_luong['BHXH (10.5%)'] = (df_luong['Lương Gross'] * 0.105).round()
            df_luong['Thu nhập tính thuế'] = df_luong['Lương Gross'] - df_luong['BHXH (10.5%)'] - 11000000
            df_luong['Thuế TNCN'] = df_luong['Thu nhập tính thuế'].apply(tinh_thue_tncn)
            df_luong['NET Thực Nhận'] = df_luong['Lương Gross'] - df_luong['BHXH (10.5%)'] - df_luong['Thuế TNCN']
            
            st.dataframe(
                df_luong[['full_name', 'so_cong_thuc_te', 'Lương Gross', 'BHXH (10.5%)', 'Thuế TNCN', 'NET Thực Nhận']]
                .style.format({
                    "Lương Gross": "{:,.0f}",
                    "BHXH (10.5%)": "{:,.0f}",
                    "Thuế TNCN": "{:,.0f}",
                    "NET Thực Nhận": "{:,.0f}"
                }),
                use_container_width=True
            )
            conn.close()

    # --- GIAO DIỆN NHÂN VIÊN ---
   # --- GIAO DIỆN NHÂN VIÊN ---
    elif st.session_state.role == 'employee':
        import os # Thêm thư viện os để load ảnh (nếu trên cùng file chưa import)
        
        # Chia làm 2 Tab cho gọn gàng
        tab_info, tab_cong = st.tabs(["👤 Thông tin cá nhân", "📅 Bảng chấm công"])
        
        # TAB 1: THÔNG TIN CÁ NHÂN
        with tab_info:
            st.subheader("Hồ sơ Nhân viên")
            
            # Kéo thông tin chi tiết từ DB
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT username, full_name, daily_rate, phu_cap FROM users WHERE username=%s", (st.session_state.username,))
            user_info = cur.fetchone()
            conn.close()
            
            if user_info:
                # Chia 2 cột: Cột 1 để ảnh, Cột 2 để text
                col_img, col_text = st.columns([1, 2])
                
                with col_img:
                    # Trích xuất ảnh từ thư mục raw_image của hệ thống nhận diện
                    img_path = f"raw_image/{st.session_state.username}/{st.session_state.username}_0.jpg"
                    if os.path.exists(img_path):
                        st.image(img_path, width=200, caption="Ảnh đại diện (AI Camera)")
                    else:
                        # Nếu chưa có ảnh nhận diện, dùng avatar mặc định
                        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=200, caption="Ảnh mặc định")
                
                with col_text:
                    st.markdown(f"**Họ và tên:** {user_info[1]}")
                    st.markdown(f"**Mã nhân viên:** {user_info[0]}")
                    st.markdown(f"**Chức vụ:** Nhân viên")
                    # Lưu ý: Vì DB hiện tại chưa có cột phòng ban, mình đang để mặc định. 
                    st.markdown(f"**Phòng ban:** Khối Vận hành") 
                    st.markdown(f"**Mức lương cơ bản:** {user_info[2]:,.0f} VNĐ/Tháng")
                    st.markdown(f"**Phụ cấp cố định:** {user_info[3]:,.0f} VNĐ/Tháng")

        # TAB 2: BẢNG CHẤM CÔNG (Giữ nguyên logic cũ của bạn)
        with tab_cong:
            st.subheader(f"Bảng công của bạn tháng này")
            conn = get_connection()
            
            query = "SELECT date, check_in, check_out, status, earned_money FROM attendance WHERE username=%s"
            df_personal = pd.read_sql(query, conn, params=(st.session_state.username,))
            
            if not df_personal.empty:
                df_personal = df_personal.rename(columns={
                    'date': 'Ngày',
                    'check_in': 'Giờ đến',
                    'check_out': 'Giờ về',
                    'status': 'Trạng thái',
                    'earned_money': 'Lương ngày'
                })
                
                st.table(df_personal.style.format({"Lương ngày": "{:,.0f}"}))
                
                total = df_personal['Lương ngày'].sum()
                st.metric("Tổng thu nhập tạm tính", f"{total:,.0f} VNĐ")
            else:
                st.info("Chưa có dữ liệu chấm công cho tài khoản này.")
            conn.close()
