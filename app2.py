import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Hệ Thống Chấm Công AI", page_icon="🏢", layout="wide")

# --- CẤU HÌNH CLOUD DATABASE (SUPABASE) ---
# Thay MATKHAUCUABAN bằng mật khẩu thực tế của bạn
DATABASE_URL = "postgresql://postgres.bbhfioltprvytizmclxl:Anhngoc0205@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
# --- HÀM KẾT NỐI DATABASE ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- GIAO DIỆN ĐĂNG NHẬP (CỘT BÊN TRÁI) ---
st.sidebar.title("🔐 Đăng Nhập")
username_input = st.sidebar.text_input("Tài khoản")
password_input = st.sidebar.text_input("Mật khẩu", type="password")
login_btn = st.sidebar.button("Đăng nhập")

# Xử lý nút Đăng nhập
if login_btn:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username_input, password_input))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user:
        st.session_state['user'] = user
        st.rerun()
    else:
        st.sidebar.error("❌ Sai tài khoản hoặc mật khẩu!")

# Thêm nút Đăng xuất
if 'user' in st.session_state:
    if st.sidebar.button("Đăng xuất"):
        del st.session_state['user']
        st.rerun()

# --- GIAO DIỆN CHÍNH ---
if 'user' in st.session_state:
    user_data = st.session_state['user']
    u_username = user_data[1]  # Vị trí chuẩn trong bảng users là 1
    u_fullname = user_data[3]  # Vị trí chuẩn là 3
    u_role = user_data[4]      # Vị trí chuẩn là 4
    u_daily_rate = user_data[5]# Vị trí chuẩn là 5

    # ================= GIAO DIỆN ADMIN =================
    if u_role == 'admin':
        st.title(f"🛠️ Bảng Điều Khiển Admin")
        st.write(f"Xin chào Quản trị viên: **{u_fullname}**")
        
        tab1, tab2 = st.tabs(["👥 Quản lý Nhân viên", "📊 Báo cáo Chấm công"])
        
        with tab1:
            st.subheader("Cấp phát tài khoản nhân viên")
            with st.form("add_user_form"):
                new_username = st.text_input("Tên tài khoản (Ví dụ: ngocanh)")
                new_fullname = st.text_input("Họ và Tên thật")
                new_password = st.text_input("Mật khẩu")
                new_rate = st.number_input("Lương 1 ngày (VNĐ)", min_value=0, step=10000)
                submit_add = st.form_submit_button("Thêm Nhân Viên")
                
                if submit_add:
                    if new_username and new_fullname and new_password:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("INSERT INTO users (username, password, full_name, role, daily_rate) VALUES (%s, %s, %s, %s, %s)",
                                         (new_username, new_password, new_fullname, 'employee', new_rate))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"✅ Đã thêm nhân viên {new_fullname} thành công!")
                        except psycopg2.IntegrityError:
                            st.error("❌ Tên tài khoản này đã tồn tại!")
                    else:
                        st.warning("Vui lòng điền đủ thông tin.")

            st.write("---")
            st.write("**Danh sách tài khoản hiện tại:**")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, username, full_name, role, daily_rate FROM users")
            df_users = pd.DataFrame(cur.fetchall(), columns=['id', 'username', 'full_name', 'role', 'daily_rate'])
            cur.close()
            conn.close()
            # Format lương ngày ở bảng Admin
            st.dataframe(df_users.style.format({"daily_rate": "{:,.0f}"}), use_container_width=True)

        with tab2:
            st.subheader("Lịch sử ra vào của toàn Công ty")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM attendance ORDER BY date DESC, check_in DESC")
            col_names = [desc[0] for desc in cur.description] # Lấy tên cột từ database
            df_all = pd.DataFrame(cur.fetchall(), columns=col_names)
            cur.close()
            conn.close()
            
            if not df_all.empty:
                # Format lương thực nhận ở bảng Admin
                st.dataframe(df_all.style.format({"earned_money": "{:,.0f}"}), use_container_width=True)
            else:
                st.info("Chưa có dữ liệu chấm công nào.")

    # ================= GIAO DIỆN NHÂN VIÊN =================
    elif u_role == 'employee':
        st.title(f"👋 Chào mừng, {u_fullname}")
        st.info(f"💰 Mức lương cơ bản của bạn: **{u_daily_rate:,.0f} VNĐ / Ngày**")
        
        st.subheader("📅 Bảng công cá nhân của bạn")
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT date, check_in, check_out, status, earned_money FROM attendance WHERE username=%s ORDER BY date DESC", (u_username,))
        df_emp = pd.DataFrame(cur.fetchall(), columns=['Ngày', 'Giờ đến', 'Giờ về', 'Trạng thái', 'Lương ngày'])
        cur.close()
        conn.close()
        
        if not df_emp.empty:
            def color_status(val):
                if val == 'Đúng giờ': return 'color: #28a745; font-weight: bold;'
                elif val == 'Đi muộn': return 'color: #fd7e14; font-weight: bold;'
                elif val == 'Thiếu công': return 'color: #dc3545; font-weight: bold;'
                return ''
            
            styled_df = df_emp.style.format({"Lương ngày": "{:,.0f}"}).map(color_status, subset=['Trạng thái'])
            st.dataframe(styled_df, use_container_width=True)
            
            total_salary = df_emp['Lương ngày'].sum()
            st.success(f"💵 TỔNG LƯƠNG TẠM TÍNH: **{total_salary:,.0f} VNĐ**")
        else:
            st.info("Bạn chưa có dữ liệu chấm công nào trên hệ thống.")

else:
    st.info("👈 Vui lòng nhập tài khoản và mật khẩu ở thanh bên trái.")
