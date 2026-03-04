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
                new_user = st.text_input("Username mới")
                new_pw = st.text_input("Password mới", type="password")
                new_name = st.text_input("Họ tên đầy đủ")
            with col_b:
                new_rate = st.number_input("Lương cơ bản (Tháng)", min_value=0, step=1000000)
                new_phucap = st.number_input("Phụ cấp (Xăng, ăn...)", min_value=0, step=100000)
            
            if st.button("Tạo tài khoản"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO users (username, password, full_name, role, daily_rate, phu_cap) VALUES (%s, %s, %s, %s, %s, %s)",
                                (new_user, new_pw, new_name, 'employee', new_rate, new_phucap))
                    conn.commit()
                    st.success(f"Đã tạo thành công tài khoản cho {new_name}")
                    conn.close()
                except:
                    st.error("Lỗi: Username đã tồn tại hoặc thiếu cột phu_cap trong DB!")

        with tab2:
            st.subheader("Danh sách nhân sự và Quản lý")
            conn = get_connection()
            # Lấy thêm trường password từ Database
            df_u = pd.read_sql("SELECT username, password, full_name, daily_rate, phu_cap FROM users WHERE role='employee'", conn)
            
            for index, row in df_u.iterrows():
                # Chia làm 5 cột thay vì 4, dành không gian cho mật khẩu
                col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
                
                col1.write(f"**@{row['username']}**")
                # Dùng st.code để in mật khẩu ra, admin click vào là copy được luôn
                col2.code(row['password']) 
                col3.write(f"{row['full_name']}")
                col4.write(f"{row['daily_rate']:,}đ")
                
                # Nút xóa tài khoản
                if col5.button("Xóa", key=f"del_{row['username']}"):
                    try:
                        cur = conn.cursor()
                        # 1. Xóa dữ liệu chấm công trước
                        cur.execute("DELETE FROM attendance WHERE username=%s", (row['username'],))
                        # 2. Xóa tài khoản
                        cur.execute("DELETE FROM users WHERE username=%s", (row['username'],))
                        conn.commit()
                        st.warning(f"Đã xóa tài khoản {row['username']}")
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Lỗi khi xóa: {e}")
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
    else:
        st.subheader(f"Bảng công của bạn: {st.session_state.full_name}")
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
            
            # ĐÃ SỬA: Ép định dạng cột Lương ngày bỏ số thập phân và thêm dấu phẩy
            st.table(df_personal.style.format({"Lương ngày": "{:,.0f}"}))
            
            total = df_personal['Lương ngày'].sum()
            st.metric("Tổng thu nhập tạm tính", f"{total:,.0f} VNĐ")
        else:
            st.info("Chưa có dữ liệu chấm công cho tài khoản này.")
        conn.close()
