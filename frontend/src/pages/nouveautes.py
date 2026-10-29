import streamlit as st

from frontend.styles.maj_260122 import st_maj260122


def afficher():

    st.header("📢 Nouveautés & Mises à jour")

    # --- MISE A JOUR V2.1 ---
    with st.container(border=True):
        st.subheader("💎 Mise à jour v2.1 : Trophées & Rivalités")
        st.caption("Déployée le 22 Janvier 2026")

        st.markdown(st_maj260122)
