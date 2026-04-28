import streamlit as st
import pandas as pd
import time
import calendar
from datetime import date, timedelta
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO VISUAL ---
try:
    st.set_page_config(page_title="Controle de Notas Fiscais", page_icon="logo.png", layout="centered")
except:
    st.set_page_config(page_title="Controle de Notas Fiscais", page_icon="📝", layout="centered")

# --- CABEÇALHO ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo.png", width=100)
    except:
        st.caption("") 
with col_titulo:
    st.title("Controle de Notas Fiscais")

# --- 2. CONEXÃO SEGURA ---
try:
    URL_SUPABASE = st.secrets["SUPABASE_URL"]
    KEY_SUPABASE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)
except Exception as e:
    st.error("⚠️ Erro de Conexão. Verifique os Secrets.")
    st.stop()

# ==========================================
# --- MOTOR DE COBRANÇA (A PARTIR DE HOJE) ---
# ==========================================
def exibir_painel_alertas():
    DIAS_AVISO_PREVIO = 2 

    REGRAS = {
        "AgiBank": {"tipo": "dia_util", "dia": 1},
        "Capital": {"tipo": "semanal", "dias": 7},
        "Amigoz": {"tipo": "dia_fixo", "dia": 1}, 
        "Banrisul": {"tipo": "dia_fixo", "dia": 29}, 
        "Banco do Brasil": {"tipo": "dia_util", "dia": 3},
        "BMG": {"tipo": "dia_fixo", "dia": 16},
        "BRB": {"tipo": "dia_util", "dia": 5},
        "C6 Bank": {"tipo": "dia_util", "dia": 1},
        "CBA": {"tipo": "dia_fixo", "dia": 1},
        "CCB": {"tipo": "dia_util", "dia": 1},
        "Crefaz": {"tipo": "semanal", "dias": 7},
        "Crefisa": {"tipo": "dia_fixo", "dia": 28},
        "Daycoval": {"tipo": "ultimo_dia"},
        "Digio": {"tipo": "dia_util", "dia": 3},
        "Happy": {"tipo": "dia_fixo", "dia": 1},
        "iCred": {"tipo": "dia_util", "dia": 3},
        "Itaú": {"tipo": "dia_fixo", "dia": 17},
        "Mercantil TL": {"tipo": "dia_util", "dia": 1},
        "Mercantil CP": {"tipo": "semanal", "dias": 7},
        "Pan": {"tipo": "dia_util", "dia": 3},
        "Paraná": {"tipo": "dia_fixo", "dia": 14},
        "PicPay": {"tipo": "dia_util", "dia": 3},
        "PresençaBank": {"tipo": "dia_util", "dia": 1},
        "Santander": {"tipo": "semanal", "dias": 7},
        "BTW": {"tipo": "dia_fixo", "dia": 1},
        "BRB360": {"tipo": "dia_fixo", "dia": 25},
        "Safra": {"tipo": "dia_util", "dia": 3},
        "QueroMais": {"tipo": "ultimo_dia"}
    }

    try:
        res = supabase.table("notas_fiscais").select("banco, data_emissao, emitida").eq("emitida", True).execute()
        df_emitidas = pd.DataFrame(res.data)
        
        hoje = date.today()
        cal = calendar.Calendar()
        dias_uteis = [d for d in cal.itermonthdates(hoje.year, hoje.month) if d.month == hoje.month and d.weekday() < 5]
        
        atrasados = []
        vencendo_em_breve = []

        for banco, regra in REGRAS.items():
            nunca_emitido = True
            
            if not df_emitidas.empty:
                df_b = df_emitidas[df_emitidas['banco'] == banco]
                if not df_b.empty:
                    ultima = pd.to_datetime(df_b['data_emissao'].max()).date()
                    nunca_emitido = False

            # --- LÓGICA SEMANAL ---
            if regra["tipo"] == "semanal":
                if nunca_emitido:
                    atrasados.append(f"🚨 **{banco}**: Emissão semanal pendente!")
                else:
                    dias_sem_nota = (hoje - ultima).days
                    if dias_sem_nota > 7:
                        atrasados.append(f"🚨 **{banco}**: Atrasado há {dias_sem_nota - 7} dias! (Regra: Semanal)")
                    elif dias_sem_nota >= (7 - DIAS_AVISO_PREVIO):
                        vencendo_em_breve.append(f"⚠️ **{banco}**: Prazo semanal vence em {7 - dias_sem_nota} dias.")

            # --- LÓGICA MENSAL ---
            else:
                if regra["tipo"] == "dia_util":
                    idx = regra["dia"] - 1
                    data_limite = dias_uteis[idx] if idx < len(dias_uteis) else dias_uteis[-1]
                elif regra["tipo"] == "dia_fixo":
                    try: data_limite = hoje.replace(day=regra["dia"])
                    except: data_limite = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
                elif regra["tipo"] == "ultimo_dia":
                    data_limite = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

                # Verifica se já emitiu DENTRO DESTE MÊS
                ja_emitiu_mes_atual = (not nunca_emitido) and (ultima >= hoje.replace(day=1))

                if not ja_emitiu_mes_atual:
                    if hoje > data_limite:
                        atrasados.append(f"🚨 **{banco}**: ATRASADO! (Venceu dia {data_limite.strftime('%d/%m')})")
                    elif (data_limite - hoje).days <= DIAS_AVISO_PREVIO:
                        vencendo_em_breve.append(f"⚠️ **{banco}**: Vence em {(data_limite - hoje).days} dias ({data_limite.strftime('%d/%m')})")

        # --- EXIBIÇÃO NO TOPO ---
        if atrasados or vencendo_em_breve:
            st.toast("⚠️ Existem notas pendentes!", icon="🚨")
            with st.container():
                st.error("## 📢 CENTRAL DE COBRANÇA")
                
                if atrasados:
                    st.markdown("#### 🚩 PENDENTES / ATRASADOS")
                    for a in atrasados:
                        st.write(a)
                
                if vencendo_em_breve:
                    st.markdown("#### ⏳ VENCENDO EM BREVE")
                    for v in vencendo_em_breve:
                        st.info(v)
                st.write("---")
    except Exception as e:
        pass

exibir_painel_alertas()

# --- 3. FUNÇÃO MESTRA (ABAS E LANÇAMENTOS) ---
def desenhar_aba_codigo(codigo_atual):
    listas_de_bancos = {
        "TN": ["AgiBank", "Banrisul", "BMG", "BOC", "C6 Bank", "Cetelem", "CredFranco", "Crefaz", "Daycoval", "Digio", "Diga", "Facta", "Itaú", "Master", "Pan", "Paraná", "PresençaBank", "Santander", "PicPay", "Voce Seguradora", "QueroMais", "TeddyHub"],
        "TL": ["Amigoz", "Banrisul", "Banco do Brasil", "BMG", "BRB", "BTW", "CBA", "C6 Bank", "Capital", "CredFranco", "Crefisa", "Digio", "Facta", "Futuro Previdência", "GVN", "Happy", "iCred", "Itaú", "Lecca", "Nossa Fintech", "Pan", "Santander", "ZiliCred", "Safra"],
        "JF": ["Daycoval", "Santander"]
    }
    opcoes_bancos = listas_de_bancos.get(codigo_atual, ["Outros"])
    lista_categorias = ["Comissão a Vista", "Pro-Rata", "Campanha", "Seguro"]
    if codigo_atual in ["TN", "TL"]: lista_categorias.append("Auto (C6)")

    st.markdown(f"### Gestão: **{codigo_atual}**")
    
    with st.expander(f"➕ Nova Nota ({codigo_atual})", expanded=True):
        with st.form(f"form_{codigo_atual}", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                banco = st.selectbox("Banco", options=opcoes_bancos, key=f"b_{codigo_atual}")
                categoria = st.selectbox("Tipo de Recebimento", options=lista_categorias, key=f"cat_{codigo_atual}")
                data_em = st.date_input("Data de Emissão", value=date.today(), key=f"d_{codigo_atual}")
            with col2:
                num_nf = st.text_input("Número da NF", key=f"n_{codigo_atual}")
                data_ref_input = st.date_input("Mês de Referência", value=date.today(), key=f"ref_{codigo_atual}")
                status_emitida = st.toggle("Marcar como Emitida", key=f"t_{codigo_atual}")
            
            if st.form_submit_button("💾 Salvar Lançamento"):
                if not num_nf: st.warning("⚠️ Informe o número da NF.")
                elif categoria == "Auto (C6)" and "C6" not in banco: st.error("⛔ Categoria Auto é só para C6.")
                else:
                    try:
                        ref_formatada = data_ref_input.strftime("%m/%Y")
                        dados = {
                            "codigo": codigo_atual, "banco": banco, "categoria": categoria, 
                            "referencia": ref_formatada, "data_emissao": str(data_em), 
                            "numero_nf": num_nf, "emitida": status_emitida
                        }
                        supabase.table("notas_fiscais").insert(dados).execute()
                        st.success("Salvo com sucesso!")
                        time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    # --- HISTÓRICO ---
    st.write("---")
    try:
        res = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("data_emissao", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_emissao'] = pd.to_datetime(df['data_emissao'])
            df['STATUS'] = df['emitida'].apply(lambda x: "🟢 Emitida" if x else "🔴 Pendente")
            df['Mes/Ano'] = df['data_emissao'].dt.strftime('%m/%Y')
            st.dataframe(df[['STATUS', 'referencia', 'banco', 'categoria', 'numero_nf', 'data_emissao']], hide_index=True, use_container_width=True)
    except: st.caption("Sem dados históricos.")

# --- ABAS ---
tab1, tab2, tab3 = st.tabs(["Código TN", "Código TL", "Código JF"])
with tab1: desenhar_aba_codigo("TN")
with tab2: desenhar_aba_codigo("TL")
with tab3: desenhar_aba_codigo("JF")
