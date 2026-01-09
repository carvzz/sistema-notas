import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Gestão de Notas", layout="centered")
st.title("🗂️ Controle de Notas Fiscais")

# --- 2. CONEXÃO SEGURA (SUPABASE) ---
try:
    URL_SUPABASE = st.secrets["https://ylbilxljkqnxgkypydgw.supabase.co"]
    KEY_SUPABASE = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlsYmlseGxqa3FueGdreXB5ZGd3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc5MTgyNTAsImV4cCI6MjA4MzQ5NDI1MH0.ZFs69SUWHTLA9E7Y7nNCrF4Z8iI475usayCjqulEKt4"]
    supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)
except Exception:
    st.error("⚠️ Configuração pendente: Adicione os Secrets no Streamlit Cloud.")
    st.stop()

# --- 3. FUNÇÃO QUE DESENHA CADA ABA ---
# Para não repetir código 3 vezes, criamos um "molde" que serve para TN, TL e JF
def desenhar_aba_codigo(codigo_atual):
    st.markdown(f"### Gestão do Código: **{codigo_atual}**")
    
    # --- FORMULÁRIO DE CADASTRO ---
    with st.expander(f"➕ Nova Nota ({codigo_atual})", expanded=True):
        with st.form(f"form_{codigo_atual}", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                banco = st.selectbox("Banco", ["Banco do Brasil", "Bradesco", "Itaú", "Nubank", "Caixa", "Santander"], key=f"b_{codigo_atual}")
                data_em = st.date_input("Data de Emissão", value=date.today(), key=f"d_{codigo_atual}")
                num_nf = st.text_input("Número da NF", key=f"n_{codigo_atual}")
            
            with col2:
                st.write("**Status da Emissão**")
                # O BOTÃO DE INTERRUPTOR
                status_emitida = st.toggle("Marcar como Emitida", key=f"t_{codigo_atual}")
                
                # Feedback Visual (Vermelho/Verde)
                if status_emitida:
                    st.success("🟢 NOTA EMITIDA")
                else:
                    st.error("🔴 NÃO EMITIDA")
            
            st.write("---")
            col3, col4 = st.columns(2)
            with col3:
                is_cancelada = st.checkbox("Nota Cancelada?", key=f"c_{codigo_atual}")
            with col4:
                nova_nf = st.text_input("Número da NOVA NF (se cancelada)", key=f"nn_{codigo_atual}")

            if st.form_submit_button("💾 Salvar Lançamento"):
                dados = {
                    "codigo": codigo_atual,  # Salva qual é a aba atual
                    "banco": banco,
                    "data_emissao": str(data_em),
                    "numero_nf": num_nf,
                    "emitida": status_emitida,
                    "cancelada": is_cancelada,
                    "nova_nf": nova_nf if is_cancelada else None
                }
                try:
                    supabase.table("notas_fiscais").insert(dados).execute()
                    st.toast(f"✅ Nota lançada em {codigo_atual}!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    # --- LISTAGEM POR MÊS ---
    st.write("---")
    st.subheader(f"📂 Histórico: {codigo_atual}")
    
    # Busca apenas notas deste código específico
    response = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("data_emissao", desc=True).execute()
    df = pd.DataFrame(response.data)

    if not df.empty:
        df['data_emissao'] = pd.to_datetime(df['data_emissao'])
        
        # Cria a coluna visual de Status para a tabela
        df['STATUS'] = df['emitida'].apply(lambda x: "🟢 Emitida" if x else "🔴 Pendente")
        
        # Lógica de Meses
        mapa_meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 
                      7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
        df['ano'] = df['data_emissao'].dt.year
        df['mes_num'] = df['data_emissao'].dt.month
        df['mes_nome'] = df['mes_num'].map(mapa_meses)
        
        grupos = df.groupby(['ano', 'mes_num', 'mes_nome'])
        
        # Cria as pastas (expansores)
        for (ano, mes_num, nome_mes), dados_mes in sorted(grupos, key=lambda x: (x[0][0], x[0][1]), reverse=True):
            with st.expander(f"{nome_mes} {ano} — ({len(dados_mes)} notas)"):
                # Exibe a tabela organizada
                cols_show = ['STATUS', 'banco', 'numero_nf', 'data_emissao', 'cancelada', 'nova_nf']
                st.dataframe(dados_mes[cols_show], hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma nota encontrada para este código.")

# --- 4. CRIAÇÃO DAS ABAS PRINCIPAIS ---
tab1, tab2, tab3 = st.tabs(["Código TN", "Código TL", "Código JF"])

with tab1:
    desenhar_aba_codigo("TN")
with tab2:
    desenhar_aba_codigo("TL")
with tab3:

    desenhar_aba_codigo("JF")
