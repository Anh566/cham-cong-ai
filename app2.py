import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH KẾT NỐI SUPABASE ---
# THAY "MATKHAUCUABAN" THÀNH MẬT KHẨU THỰC TẾ CỦA BẠN
DATABASE_URL = "postgresql://postgres.bbhfioltprvytizmclxl:Anhngoc0205@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# --- GIAO DIỆN ĐĂNG NHẬP ---
st.set_page_config(page_title="Hệ thống Chấm công AI", layout="wide")
st.title("🚀 Hệ Thống Quản Lý Chấm Công Công Ty")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.sidebar:
        st.subheader("Đăng nhập")
        user = st.text_input("Tên đăng nhập")
        pw = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập"):
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
            cur.close()
            conn.close()
else:
    st.sidebar.write(f"Chào, **{st.session_state.full_name}** ({st.session_state.role})")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()

    # --- GIAO DIỆN ADMIN ---
    if st.session_state.role == 'admin':
        tab1, tab2, tab3 = st.tabs(["Cấp tài khoản", "Quản lý nhân viên", "Lịch sử chấm công"])

        with tab1:
            st.subheader("Thêm nhân viên mới")
            new_user = st.text_input("Username")
            new_pw = st.text_input("Password (mặc định)")
            new_name = st.text_input("Họ tên đầy đủ")
            new_rate = st.number_input("Lương 1 ngày (VNĐ)", min_value=0, step=10000)
            
            if st.button("Tạo tài khoản"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO users (username, password, full_name, role, daily_rate) VALUES (%s, %s, %s, %s, %s)",
                                (new_user, new_pw, new_name, 'employee', new_rate))
                    conn.commit()
                    st.success(f"Đã tạo tài khoản cho {new_name}")
                    cur.close()
                    conn.close()
                except:
                    st.error("Lỗi: Username đã tồn tại!")

        with tab2:
            st.subheader("Danh sách nhân viên hiện tại")
            conn = get_connection()
            df_users = pd.read_sql("SELECT username, full_name, daily_rate FROM users WHERE role='employee'", conn)
            conn.close()
            
            for index, row in df_users.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{row['full_name']}** (@{row['username']})")
                col2.write(f"Lương: {row['daily_rate']:,}đ")
                if col3.button("Xóa", key=f"del_{row['username']}"):
                    conn = get_connection()
                    cur = conn.cursor()
                    # Xóa lịch sử chấm công trước để tránh lỗi ràng buộc
                    cur.execute("DELETE FROM attendance WHERE username=%s", (row['username'],))
                    cur.execute("DELETE FROM users WHERE username=%s", (row['username'],))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.warning(f"Đã xóa nhân viên {row['username']}")
                    st.rerun()

        with tab3:
            st.subheader("Toàn bộ lịch sử chấm công")
            conn = get_connection()
            df_att = pd.read_sql("SELECT * FROM attendance ORDER BY id DESC", conn)
            st.dataframe(df_att, use_container_width=True)
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
