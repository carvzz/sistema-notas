import streamlit as st
import pandas as pd
import time
from supabase import create_client, Client
from datetime import date

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Gestão de Notas", layout="centered")
st.title("🗂️ Controle de Notas Fiscais")

# --- 2. CONEXÃO SEGURA (SUPABASE) ---
try:
    URL_SUPABASE = st.secrets["SUPABASE_URL"]
    KEY_SUPABASE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)
except Exception as e:
    st.error("⚠️ Erro de Conexão com os Secrets.")
    st.stop()

# --- 3. FUNÇÃO QUE DESENHA CADA ABA ---
def desenhar_aba_codigo(codigo_atual):
    
    # ========================================================
    # 📍 CONFIGURAÇÃO DOS BANCOS (EDITE AQUI)
    # ========================================================
    # Aqui definimos qual lista aparece para cada código
    listas_de_bancos = {
        "TN": ["AgiBank", "Banrisul", "C6 Bank", "Digio", "Itaú", "Caixa", "Santander", "PicPay", "QueroMais"],          # Bancos só do TN
        "TL": ["Amigoz", "Banrisul", "Banco do Brasil", "C6 Bank", "CBA", "Happy",],                      # Bancos só do TL
        "JF": ["Daycoval", "Santander"] # Bancos só do JF
    }
    
    # O sistema pega a lista certa automaticamente aqui:
    # Se por acaso o código não tiver lista (erro), usa uma genérica
    opcoes_bancos = listas_de_bancos.get(codigo_atual, ["Outros"])
    # ========================================================

    st.markdown(f"### Gestão do Código: **{codigo_atual}**")
    
    # --- FORMULÁRIO DE CADASTRO ---
    with st.expander(f"➕ Nova Nota ({codigo_atual})", expanded=True):
        with st.form(f"form_{codigo_atual}", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # AQUI O SISTEMA USA A LISTA ESPECÍFICA QUE CRIAMOS ACIMA
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

            if st.form_submit_button("💾 Salvar Lançamento"):
                if not num_nf:
                    st.warning("⚠️ Preencha o número da Nota Fiscal.")
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
                        st.success(f"✅ Nota salva em {codigo_atual}!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao gravar no banco: {e}")

    # --- LISTAGEM POR MÊS ---
    st.write("---")
    st.subheader(f"📂 Histórico: {codigo_atual}")
    
    try:
        response = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("data_emissao", desc=True).execute()
        df = pd.DataFrame(response.data)

        if not df.empty:
            df['data_emissao'] = pd.to_datetime(df['data_emissao'])
            df['STATUS'] = df['emitida'].apply(lambda x: "🟢 Emitida" if x else "🔴 Pendente")
            
            mapa_meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 
                          7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
            df['ano'] = df['data_emissao'].dt.year
            df['mes_num'] = df['data_emissao'].dt.month
            df['mes_nome'] = df['mes_num'].map(mapa_meses)
            
            grupos = df.groupby(['ano', 'mes_num', 'mes_nome'])
            
            for (ano, mes_num, nome_mes), dados_mes in sorted(grupos, key=lambda x: (x[0][0], x[0][1]), reverse=True):
                with st.expander(f"{nome_mes} {ano} — ({len(dados_mes)} notas)"):
                    cols_show = ['STATUS', 'banco', 'numero_nf', 'data_emissao', 'cancelada', 'nova_nf']
                    st.dataframe(dados_mes[cols_show], hide_index=True, use_container_width=True)
        else:
            st.info(f"Nenhuma nota lançada para o código {codigo_atual} ainda.")
            
    except Exception as e:
        st.error("Erro ao carregar dados. Verifique sua conexão.")

# --- 4. CRIAÇÃO DAS ABAS PRINCIPAIS ---
tab1, tab2, tab3 = st.tabs(["Código TN", "Código TL", "Código JF"])

with tab1:
    desenhar_aba_codigo("TN")
with tab2:
    desenhar_aba_codigo("TL")
with tab3:
    desenhar_aba_codigo("JF")

