import streamlit as st
import pandas as pd
import time
from supabase import create_client, Client
from datetime import date

# --- 1. CONFIGURAÇÃO VISUAL ---
# Tenta usar a logo. Se não achar, usa um emoji padrão.
try:
    st.set_page_config(
        page_title="Controle de Notas Fiscais",
        page_icon="logo.png", 
        layout="centered"
    )
except:
    st.set_page_config(page_title="Controle de Notas Fiscais", page_icon="📝", layout="centered")

# --- CABEÇALHO COM LOGO ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo.png", width=100)
    except:
        st.caption("") # Fica vazio se não tiver logo
with col_titulo:
    st.title("Controle de Notas Fiscais")

# --- 2. CONEXÃO SEGURA (SUPABASE) ---
try:
    URL_SUPABASE = st.secrets["SUPABASE_URL"]
    KEY_SUPABASE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)
except Exception as e:
    st.error("⚠️ Erro de Conexão. Verifique os Secrets no Streamlit Cloud.")
    st.stop()

# --- 3. FUNÇÃO MESTRA (DESENHA AS ABAS) ---
def desenhar_aba_codigo(codigo_atual):
    
    # === LISTAS DE BANCOS ATUALIZADA ===
    listas_de_bancos = {
        "TN": ["AgiBank", "Banrisul", "C6 Bank", "Digio", "Itaú", "Caixa", "Santander", "PicPay", "QueroMais"],
        "TL": ["Amigoz", "Banrisul", "Banco do Brasil", "C6 Bank", "CBA", "Happy"],
        "JF": ["Daycoval", "Santander"]
    }
    
    # Pega a lista certa ou usa "Outros" se der erro
    opcoes_bancos = listas_de_bancos.get(codigo_atual, ["Outros"])

    st.markdown(f"### Gestão: **{codigo_atual}**")
    
    # -------------------------------------------
    # ÁREA 1: FORMULÁRIO
    # -------------------------------------------
    with st.expander(f"➕ Nova Nota ({codigo_atual})", expanded=True):
        with st.form(f"form_{codigo_atual}", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                banco = st.selectbox("Banco", options=opcoes_bancos, key=f"b_{codigo_atual}")
                data_em = st.date_input("Data de Emissão", value=date.today(), key=f"d_{codigo_atual}")
                num_nf = st.text_input("Número da NF", key=f"n_{codigo_atual}")
            
            with col2:
                st.write("**Status da Emissão**")
                status_emitida = st.toggle("Marcar como Emitida", key=f"t_{codigo_atual}")
                
                if status_emitida:
                    st.success("🟢 STATUS: EMITIDA")
                else:
                    st.error("🔴 STATUS: NÃO EMITIDA")
            
            st.write("---")
            col3, col4 = st.columns(2)
            with col3:
                is_cancelada = st.checkbox("Nota Cancelada?", key=f"c_{codigo_atual}")
            with col4:
                nova_nf = st.text_input("Nova NF (se cancelada)", key=f"nn_{codigo_atual}")

            if st.form_submit_button("💾 Salvar"):
                if not num_nf:
                    st.warning("⚠️ Preencha o número da Nota.")
                else:
                    dados = {
                        "codigo": codigo_atual,
                        "banco": banco,
                        "data_emissao": str(data_em),
                        "numero_nf": num_nf,
                        "emitida": status_emitida,
                        "cancelada": is_cancelada,
                        "nova_nf": nova_nf if is_cancelada else None
                    }
                    try:
                        supabase.table("notas_fiscais").insert(dados).execute()
                        st.success(f"✅ Salvo!")
                        time.sleep(1) # Aguarda 1s para garantir
                        st.rerun()    # Atualiza a tela
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

    # -------------------------------------------
    # ÁREA 2: EXCLUSÃO
    # -------------------------------------------
    with st.expander("🗑️ Excluir Nota Errada"):
        try:
            # Busca todas as colunas (*) para evitar erros
            res_delete = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("id", desc=True).limit(30).execute()
            
            if res_delete.data:
                opcoes_exclusao = {f"NF {item['numero_nf']} - {item['banco']} ({item['data_emissao']})": item['id'] for item in res_delete.data}
                
                nota_selecionada = st.selectbox("Selecione para apagar:", list(opcoes_exclusao.keys()), key=f"sel_del_{codigo_atual}")
                
                if st.button(f"Apagar Nota ({codigo_atual})", type="primary", key=f"btn_del_{codigo_atual}"):
                    id_para_apagar = opcoes_exclusao[nota_selecionada]
                    supabase.table("notas_fiscais").delete().eq("id", id_para_apagar).execute()
                    st.toast("🗑️ Apagado!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.caption("Nenhuma nota recente para apagar.")
        except:
            st.caption("Lista de exclusão vazia.")

    # -------------------------------------------
    # ÁREA 3: HISTÓRICO VISUAL
    # -------------------------------------------
    st.write("---")
    st.subheader(f"📂 Histórico: {codigo_atual}")
    
    try:
        response = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("data_emissao", desc=True).execute()
        df = pd.DataFrame
