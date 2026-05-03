import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import os

# --- CẤU HÌNH KẾT NỐI ---
# --- CẤU HÌNH KẾT NỐI ---
DATABASE_URL = st.secrets["DATABASE_URL"]
def get_connection():
    return psycopg2.connect(DATABASE_URL)

st.set_page_config(page_title="Hệ thống Tính Lương Chuẩn", layout="wide")

# --- ẨN BIỂU TƯỢNG GITHUB VÀ MENU THỪA ---
hide_github_style = """
    <style>
    /* Ẩn nút GitHub/Fork ở góc trên bên phải */
    .stAppToolbar {display: none;}
    
    /* Ẩn biểu tượng mỏ neo (Anchor) cạnh các tiêu đề */
    .element-container:has(header) a {display: none;}
    header a {display: none !important;}
    
    /* Ẩn menu 3 chấm */
    #MainMenu {visibility: hidden;}
    
    /* Ẩn dòng "Made with Streamlit" */
    footer {visibility: hidden;}
    
    /* Ẩn header mặc định của Streamlit */
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_github_style, unsafe_allow_html=True)

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
                    new_user = st.text_input("Mã nhân viên (Dùng để đăng nhập) *") # Ví dụ: NV001
                    new_pw = st.text_input("Mật khẩu *", type="password")
                    new_name = st.text_input("Họ tên đầy đủ *")
                    # DÒNG MỚI: Nhập tên thư mục trong raw_image
                    new_face_id = st.text_input("Tên thư mục ảnh (trong raw_image) *", placeholder="Ví dụ: anhngoc")
                    
                with col_b:
                    new_phongban = st.selectbox("Phòng ban", ["IT", "Nhân sự", "Kế toán", "Marketing", "Vận hành", "Khác"])
                    new_rate = st.number_input("Lương cơ bản", min_value=0, step=1000000)
                    new_phucap = st.number_input("Phụ cấp", min_value=0, step=100000)
                
                if st.form_submit_button("Tạo tài khoản"):
                    if not new_user or not new_face_id:
                        st.warning("⚠️ Vui lòng nhập Mã nhân viên và Tên thư mục ảnh!")
                    else:
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            # Lưu thêm cột face_id
                            cur.execute("""
                                INSERT INTO users (username, password, full_name, role, daily_rate, phu_cap, phong_ban, face_id) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (new_user, new_pw, new_name, 'employee', new_rate, new_phucap, new_phongban, new_face_id))
                            conn.commit()
                            st.success(f"✅ Đã tạo tài khoản {new_user} liên kết với ảnh {new_face_id}")
                            conn.close()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")
        with tab2:
            st.subheader("👥 Danh sách nhân sự và Liên kết khuôn mặt")
            conn = get_connection()
            
            # Lấy thông tin nhân viên từ Database
            query_u = "SELECT username, password, full_name, phong_ban, daily_rate, phu_cap, face_id FROM users WHERE role='employee' ORDER BY username ASC"
            df_u = pd.read_sql(query_u, conn)
            
            if df_u.empty:
                st.info("Chưa có nhân viên nào trong hệ thống.")
            else:
                for index, row in df_u.iterrows():
                    # Hiển thị dòng tóm tắt thông tin nhân viên
                    col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 3, 2, 2])
                    col1.write(f"**{row['username']}**") # Mã nhân viên
                    col2.code(row['password'])           # Mật khẩu (dạng code để dễ copy)
                    col3.write(f"{row['full_name']} ({row['phong_ban']})")
                    col4.write(f"📁 AI: `{row['face_id']}`") # Tên thư mục ảnh
                    
                    with col5:
                        btn_edit, btn_del = st.columns(2)
                        # Nút Xóa nhân viên
                        if btn_del.button("Xóa", key=f"del_{row['username']}"):
                            cur = conn.cursor()
                            # Nhờ CASCADE, khi xóa user thì attendance tự mất theo
                            cur.execute("DELETE FROM users WHERE username=%s", (row['username'],))
                            conn.commit()
                            st.cache_data.clear()
                            st.rerun()

                        # Nút bật/tắt chế độ Chỉnh sửa
                        edit_toggle = btn_edit.toggle("Sửa", key=f"tg_{row['username']}")

                    # GIAO DIỆN CHỈNH SỬA CHI TIẾT
                    if edit_toggle:
                        with st.container(border=True):
                            st.markdown(f"⚙️ **Chỉnh sửa tài khoản:** `{row['username']}`")
                            with st.form(key=f"form_edit_{row['username']}"):
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    # Cho phép sửa Mã nhân viên (Username)
                                    new_user_val = st.text_input("Mã nhân viên mới", value=row['username'])
                                    edit_pw = st.text_input("Mật khẩu mới", value=row['password'])
                                with c2:
                                    edit_name = st.text_input("Họ tên đầy đủ", value=row['full_name'])
                                    # Sửa AI ID (tên thư mục ảnh trong raw_image)
                                    edit_face = st.text_input("Thư mục ảnh (AI ID)", value=row['face_id'])
                                with c3:
                                    list_phong = ["IT", "Nhân sự", "Kế toán", "Marketing", "Vận hành", "Khác"]
                                    idx_p = list_phong.index(row['phong_ban']) if row['phong_ban'] in list_phong else 5
                                    edit_phong = st.selectbox("Phòng ban", list_phong, index=idx_p)
                                    
                                    col_l, col_p = st.columns(2)
                                    edit_rate = col_l.number_input("Lương tháng", value=int(row['daily_rate']), step=500000)
                                    edit_pc = col_p.number_input("Phụ cấp", value=int(row['phu_cap']), step=100000)
                                
                                if st.form_submit_button("💾 Xác nhận thay đổi"):
                                    try:
                                        cur = conn.cursor()
                                        # CHỈ CẦN UPDATE BẢNG USERS. 
                                        # Lệnh này sẽ kích hoạt CASCADE trong Supabase để tự đổi bảng Attendance.
                                        cur.execute("""
                                            UPDATE users 
                                            SET username=%s, password=%s, full_name=%s, phong_ban=%s, daily_rate=%s, phu_cap=%s, face_id=%s 
                                            WHERE username=%s
                                        """, (new_user_val, edit_pw, edit_name, edit_phong, edit_rate, edit_pc, edit_face, row['username']))
                                        
                                        rows_affected = cur.rowcount 
                                        conn.commit()
                                        st.cache_data.clear()
                                        st.success(f"✅ Đã cập nhật thành công cho {new_user_val}!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Lỗi: {e}. Có thể mã nhân viên '{new_user_val}' đã tồn tại!")
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
            # Tất cả code ở đây phải thụt lề vào 1 mức so với "with tab4"
            st.subheader("💰 Phê duyệt Bảng lương tháng")
            
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                cong_chuan = st.number_input("Số ngày công chuẩn (ví dụ 26)", value=26)
            with col_cfg2:
                st.write("") 
                if st.button("🔄 Làm mới dữ liệu"):
                    st.rerun()

            conn = get_connection()
            query = """
                SELECT 
                    u.username, u.full_name, u.daily_rate as luong_thang, u.phu_cap,
                    COUNT(DISTINCT a.date) as so_ngay_di_lam, 
                    SUM(a.earned_money) as tong_tien_cong_thuc_te
                FROM users u
                LEFT JOIN attendance a ON u.username = a.username
                WHERE u.role = 'employee'
                GROUP BY u.username, u.full_name, u.daily_rate, u.phu_cap
            """
            df_luong = pd.read_sql(query, conn)
            
            if not df_luong.empty:
                df_luong['Lương Gross'] = df_luong['tong_tien_cong_thuc_te'] + df_luong['phu_cap']
                df_luong['BHXH (10.5%)'] = (df_luong['Lương Gross'] * 0.105).round()
                df_luong['TNTT'] = (df_luong['Lương Gross'] - df_luong['BHXH (10.5%)'] - 11000000).clip(lower=0)
                df_luong['Thuế TNCN'] = df_luong['TNTT'].apply(tinh_thue_tncn)
                df_luong['NET Thực Nhận'] = df_luong['Lương Gross'] - df_luong['BHXH (10.5%)'] - df_luong['Thuế TNCN']
                
                st.dataframe(
                    df_luong[['full_name', 'so_ngay_di_lam', 'Lương Gross', 'BHXH (10.5%)', 'Thuế TNCN', 'NET Thực Nhận']]
                    .rename(columns={'full_name': 'Họ tên', 'so_ngay_di_lam': 'Số ngày làm'})
                    .style.format({"Lương Gross": "{:,.0f}đ", "BHXH (10.5%)": "{:,.0f}đ", "Thuế TNCN": "{:,.0f}đ", "NET Thực Nhận": "{:,.0f}đ"}),
                    use_container_width=True
                )
                
                tong_quy = df_luong['NET Thực Nhận'].sum()
                st.success(f"✅ Tổng quỹ lương cần chi trả: **{tong_quy:,.0f} VNĐ**")

                # --- PHẦN XUẤT FILE EXCEL ĐÃ SỬA LỖI TÊN BIẾN ---
                st.divider()
                st.subheader("📥 Xuất báo cáo Excel")
                
                import io
                from datetime import datetime

                # 1. Chuẩn bị dữ liệu
                df_excel = df_luong[['full_name', 'so_ngay_di_lam', 'Lương Gross', 'BHXH (10.5%)', 'Thuế TNCN', 'NET Thực Nhận']].copy()
                df_excel.columns = ['Họ tên', 'Số ngày làm', 'Lương Gross', 'BHXH 10.5%', 'Thuế TNCN', 'Thực nhận NET']

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    # Ghi dữ liệu từ dòng thứ 4 (index 3)
                    df_excel.to_excel(writer, index=False, sheet_name='Bang_Luong', startrow=3)
                    
                    workbook  = writer.book
                    worksheet = writer.sheets['Bang_Luong']

                    # 2. Định dạng (Format) - Đã chuẩn hóa tên biến
                    title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
                    info_fmt = workbook.add_format({'italic': True, 'font_size': 10})
                    h_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
                    money_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1})
                    border_fmt = workbook.add_format({'border': 1})

                    # 3. Viết tiêu đề tháng
                    thang_hien_tai = datetime.now().strftime('%m/%Y')
                    worksheet.merge_range('A1:F1', f'BẢNG LƯƠNG NHÂN VIÊN - THÁNG {thang_hien_tai}', title_fmt)
                    
                    # 4. Viết ngày xuất báo cáo
                    ngay_xuat = datetime.now().strftime('%d/%m/%Y %H:%M')
                    worksheet.write('A2', f'Ngày xuất báo cáo: {ngay_xuat}', info_fmt)

                    # 5. Áp dụng định dạng cho Header (Dòng 4 - Index 3)
                    for col_num, value in enumerate(df_excel.columns.values):
                        worksheet.write(3, col_num, value, h_fmt) # Đã dùng h_fmt thống nhất
                    
                    # 6. Chỉnh độ rộng cột và định dạng số cho các cột tiền
                    worksheet.set_column('A:B', 20, border_fmt) # Cột tên và ngày làm
                    worksheet.set_column('C:F', 18, money_fmt) # Các cột tiền từ C đến F

                st.download_button(
                    label="🚀 Tải Bảng lương Excel chuẩn (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"Bang_Luong_Thang_{datetime.now().strftime('%m_%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Chưa có dữ liệu chấm công.")
            conn.close()
   # --- GIAO DIỆN NHÂN VIÊN ---
    elif st.session_state.role == 'employee':
        tab_info, tab_cong = st.tabs(["👤 Thông tin cá nhân", "📅 Bảng chấm công"])
        
        # Lấy thông tin cơ bản và face_id
        conn = get_connection()
        cur = conn.cursor()
        # BỔ SUNG: Lấy thêm face_id (cột thứ 6)
        cur.execute("SELECT username, full_name, daily_rate, phu_cap, phong_ban, face_id FROM users WHERE username=%s", (st.session_state.username,))
        user_info = cur.fetchone()
        conn.close()

        with tab_info:
            st.subheader("Hồ sơ Nhân viên")
            if user_info:
                col_img, col_text = st.columns([1, 2])
                with col_img:
                    # SỬA LỖI: Dùng face_id (user_info[5]) để load ảnh thay vì username
                    f_id = user_info[5] if user_info[5] else "unknown"
                    img_path = f"raw_image/{f_id}/{f_id}_0.jpg"
                    
                    if os.path.exists(img_path):
                        st.image(img_path, width=200, caption="Ảnh nhận diện AI")
                    else:
                        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=200, caption="Chưa có ảnh hồ sơ")
                
                with col_text:
                    st.markdown(f"**Họ và tên:** {user_info[1]}")
                    st.markdown(f"**Mã nhân viên:** {user_info[0]}") # Đây là mã ví dụ NV001
                    st.markdown(f"**AI ID (Thư mục ảnh):** `{user_info[5]}`") # Để nhân viên biết mình khớp với folder nào
                    st.markdown(f"**Phòng ban:** {user_info[4] if user_info[4] else 'Chưa cập nhật'}") 
                    st.markdown(f"**Mức lương cơ bản:** {user_info[2]:,.0f} VNĐ/Tháng")
                    st.markdown(f"**Phụ cấp cố định:** {user_info[3]:,.0f} VNĐ/Tháng")

        with tab_cong:
            st.subheader(f"Bảng công của bạn tháng này")
            conn = get_connection()
            # Sắp xếp ngày mới nhất lên đầu
            query = "SELECT date, check_in, check_out, status, earned_money FROM attendance WHERE username=%s ORDER BY date DESC"
            df_personal = pd.read_sql(query, conn, params=(st.session_state.username,))
            
            if not df_personal.empty:
                # Xử lý lặp chữ "Về sớm" hoặc "Đi muộn"
                def clean_status(x):
                    if not x: return ""
                    # Tách chuỗi bằng " & ", lọc trùng bằng dict.fromkeys, rồi nối lại
                    return " & ".join(list(dict.fromkeys(str(x).split(" & "))))

                df_personal['status'] = df_personal['status'].apply(clean_status)

                # Làm đẹp tên cột
                df_personal = df_personal.rename(columns={
                    'date': 'Ngày', 'check_in': 'Giờ đến', 'check_out': 'Giờ về',
                    'status': 'Trạng thái', 'earned_money': 'Lương ngày'
                })
                
                # Xử lý các giá trị trống
                df_personal['Giờ về'] = df_personal['Giờ về'].fillna('--:--:--')

                st.table(df_personal.style.format({"Lương ngày": "{:,.0f}"}))
                
                total = df_personal['Lương ngày'].sum()
                st.metric("Tổng thu nhập thực tế tháng này (Tạm tính)", f"{total:,.0f} VNĐ")
            else:
                st.info("Hệ thống chưa ghi nhận dữ liệu chấm công nào của bạn.")
            conn.close()
