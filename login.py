import streamlit as st
import sys
import os
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from core.auth import (
    init_session, 
    authenticate_email_password, 
    register_user, 
    get_user_by_email,
    is_login_attempts_exceeded,
    check_session_expiry,
    logout_user
)

st.set_page_config(
    page_title="Safeway - Login",
    layout="centered",
    initial_sidebar_state="collapsed"
)

init_session()

if check_session_expiry():
    st.warning("Sua sessão expirou. Por favor, faça login novamente.")

def show_login_form():
    st.title("Safeway")
    st.subheader("Login")
    
    with st.form("login_form"):
        email = st.text_input("E-mail", key="login_email")
        password = st.text_input("Senha", type="password", key="login_password")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            submit_button = st.form_submit_button("Entrar")
        
        with col2:
            register_button = st.form_submit_button("Criar Conta")

    if submit_button:
        if not email or not password:
            st.error("Por favor, preencha todos os campos.")
            return
        
        if is_login_attempts_exceeded():
            st.error("Número máximo de tentativas de login excedido. Tente novamente mais tarde.")
            return
        
        if authenticate_email_password(email, password):
            st.success("Login realizado com sucesso!")
            st.switch_page("pages/interface.py") # Redireciona para o script principal
        else:
            st.error("E-mail ou senha inválidos.")
    
    # Processar criação de conta
    if register_button:
        st.session_state.show_register = True
        st.rerun() # Precisa de rerun para mudar o formulário

def show_register_form():
    st.title("Safeway")
    st.subheader("Criar Conta")
    
    with st.form("register_form"):
        name = st.text_input("Nome", key="register_name")
        email = st.text_input("E-mail", key="register_email")
        password = st.text_input("Senha", type="password", key="register_password")
        confirm_password = st.text_input("Confirmar Senha", type="password", key="register_confirm_password")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            submit_button = st.form_submit_button("Registrar")
        
        with col2:
            back_button = st.form_submit_button("Voltar")

    if submit_button:
        if not name or not email or not password or not confirm_password:
            st.error("Por favor, preencha todos os campos.")
            return
        
        if password != confirm_password:
            st.error("As senhas não coincidem.")
            return
        
        if len(password) < 8:
            st.error("A senha deve ter pelo menos 8 caracteres.")
            return

        if get_user_by_email(email):
            st.error("Este e-mail já está em uso.")
            return

        if register_user(email, password, name):
            st.success("Conta criada com sucesso! Faça login para continuar.")
            st.session_state.show_register = False
            st.rerun()
        else:
            st.error("Erro ao criar conta. Tente novamente.")

    if back_button:
        st.session_state.show_register = False
        st.rerun()

def main():
    if st.session_state.auth:
        st.switch_page("pages/interface.py")
    
    if st.session_state.get("show_register", False):
        show_register_form()
    else:
        show_login_form()


if __name__ == "__main__":
    main()