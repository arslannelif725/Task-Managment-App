import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import date, datetime

DB_NAME = 'task_managment.db'

# --- VERİTABANI BAŞLATMA ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Kullanıcılar tablosu 
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)')
    # Görevler tablosu
    cursor.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, description TEXT, category TEXT NOT NULL, priority TEXT NOT NULL, status TEXT DEFAULT 'Yapılacak', due_date TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id))")
    conn.commit()
    conn.close()

# Veritabanını çalıştır
init_db()

# --- ŞİFRELEME FONKSİYONU ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- KULLANICI KAYIT FONKSİYONU ---
def register_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, make_hashes(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# --- KULLANICI GİRİŞ FONKSİYONU ---
def login_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, make_hashes(password)))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

# Oturum durumlarını başlat 
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = ''

# Giriş yapılmadıysa gösterilecek ekran 
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(['Giriş Yap', 'Kayıt Ol'])
    with tab1:
        st.subheader('Hesabınıza Giriş Yapın')
        l_username = st.text_input('Kullanıcı Adı', key='login_user_input')
        l_password = st.text_input('Şifre', type='password', key='login_pass_input')

        if st.button('Giriş Yap'):
            user_id = login_user(l_username, l_password)
            if user_id:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user_id
                st.session_state['username'] = l_username
                st.success('Giriş Başarılı! Yönlendiriliyorsunuz...')
                st.rerun()
            else:
                st.error('Kullanıcı adı veya şifre hatalı!')
    with tab2:
        st.subheader('Yeni Hesap Oluştur')
        r_username = st.text_input('Kullanıcı Adı', key='reg_user_input')
        r_password = st.text_input('Şifre', type='password', key='reg_pass_input')

        if st.button('Kayıt Ol'):
            if r_username and r_password:
                success = register_user(r_username, r_password)
                if success:
                    st.success('Kayıt başarılı!')
                else:
                    st.error('Bu kullanıcı adı zaten alınmış!')
            else:
                st.warning('Lütfen tüm alanları doldurun.')

# Giriş yapıldıysa ana uygulama ekranı
else:
    st.sidebar.success(f"Hoş geldin, {st.session_state['username']}!")
    if st.sidebar.button('Çıkış yap'):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['username'] = ''
        st.rerun()
        
    st.write('---')
    st.subheader('🚀 Görev Yönetim Paneli')

    # Akıllı bildirim paneli
    conn = sqlite3.connect(DB_NAME)
    df_tasks = pd.read_sql_query(
        "SELECT * FROM tasks WHERE user_id = ? AND status != 'Tamamlandı'",
        conn,
        params=(st.session_state['user_id'],)
    )
    conn.close()

    if not df_tasks.empty:
        bugun = str(date.today())
        acil_gorevler = df_tasks[df_tasks['due_date'] == bugun]

        if not acil_gorevler.empty:
            st.error(f"⚠️ Dikkat! Bugün son teslim tarihi olan {len(acil_gorevler)} adet görevin var!")
            for index, row in acil_gorevler.iterrows():
                st.warning(f"📌 **{row['title']}** ({row['category']}) - Öncelik: {row['priority']}")
                
    st.write('---')

    # Yeni görev ekleme formu
    st.subheader("📝 Yeni Görev Ekle")
    with st.form('task_form'):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input('Görev Başlığı')
            category = st.selectbox('Kategori', ['İş', 'Ders', 'Kişisel', 'Proje'])
        with col2:
            priority = st.selectbox('Öncelik Seviyesi', ['Düşük', 'Orta', 'Yüksek'])
            due_date = st.date_input('Son Teslim Tarihi', value=date.today())
            
        description = st.text_area('Görev Açıklaması (İsteğe bağlı)')
        submit_task = st.form_submit_button('Görevi Kaydet')
        
        if submit_task:
            if title:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tasks (user_id, title, description, category, priority, due_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (st.session_state['user_id'], title, description, category, priority, str(due_date)))
                conn.commit()
                conn.close()
                st.success(f"'{title}' başarıyla eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen görev başlığını boş bırakmayın.")

    st.write('---')

    # --- GÖREVLERİ LİSTELEME VE YÖNETİM ---
    st.subheader("📋 Görevlerim ve İşlemler")

    conn = sqlite3.connect(DB_NAME)
    df_all_tasks = pd.read_sql_query(
        "SELECT id, title, description, category, priority, status, due_date FROM tasks WHERE user_id = ?",
        conn,
        params=(st.session_state['user_id'],)
    )
    conn.close()

    if not df_all_tasks.empty:
        # Tabloyu göster
        st.dataframe(df_all_tasks, use_container_width=True)

        st.write("### ⚙️ Görev Durumunu Güncelle / Sil")
        
        # Seçim için görev başlıkları ve ID'leri sözlüğü
        task_options = {f"{row['title']} (Son Tarih: {row['due_date']}) - Durum: {row['status']}": row['id'] for index, row in df_all_tasks.iterrows()}
        selected_task_key = st.selectbox("İşlem yapılacak görevi seçin:", list(task_options.keys()))
        
        if selected_task_key:
            selected_task_id = task_options[selected_task_key]
            
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                if st.button("✅ Tamamlandı Yap"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tasks SET status = 'Tamamlandı' WHERE id = ?", (selected_task_id,))
                    conn.commit()
                    conn.close()
                    st.success("Görev 'Tamamlandı' olarak işaretlendi!")
                    st.rerun()
            with col_b2:
                if st.button("🔄 Devam Ediyor Yap"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tasks SET status = 'Devam Ediyor' WHERE id = ?", (selected_task_id,))
                    conn.commit()
                    conn.close()
                    st.success("Görev durumu güncellendi!")
                    st.rerun()
            with col_b3:
                if st.button("🗑️ Görevi Sil"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM tasks WHERE id = ?", (selected_task_id,))
                    conn.commit()
                    conn.close()
                    st.success("Görev başarıyla silindi!")
                    st.rerun()
    else:
        st.info("Henüz kayıtlı bir göreviniz bulunmuyor. Yukarıdan yeni bir görev ekleyebilirsiniz!")


    




    