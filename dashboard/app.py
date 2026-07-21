import streamlit as st

st.set_page_config(page_title="Piauí Primeira Infância - Dashboard", layout="wide")

pg = st.navigation(
    [
        st.Page("views/suporte.py", title="Suporte WhatsApp", icon="💬", default=True),
        st.Page("views/grupos.py", title="Grupos", icon="👥"),
    ]
)
pg.run()
