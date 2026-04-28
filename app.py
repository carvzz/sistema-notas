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
# --- MOTOR DE ALERTAS PROATIVO (POP-UP) ---
# ==========================================
def exibir_painel_alertas():
    # Configuração: Quantos dias antes do prazo começar a avisar?
    DIAS_ANTECEDENCIA = 2 

    REGRAS_ALERTAS = {
        "Capital": {"tipo": "semanal", "dias": 7},
        "Crefaz": {"tipo": "semanal", "dias": 7},
        "Santander": {"tipo": "semanal", "dias": 7},
        "Mercantil CP": {"tipo": "semanal", "dias": 7},
        "AgiBank": {"tipo": "dia_util", "dia": 1},
        "C6 Bank": {"tipo": "dia_util", "dia": 1},
        "CCB": {"tipo": "dia_util", "dia": 1},
        "Mercantil TL": {"tipo": "dia_util", "dia": 1},
        "PresençaBank": {"tipo": "dia_util", "dia": 1},
        "Banco do Brasil": {"tipo": "dia_util", "dia": 3},
        "Digio": {"tipo": "dia_util", "dia": 3},
        "iCred": {"tipo": "dia_util", "dia": 3},
        "Pan": {"tipo": "dia_util", "dia": 3},
        "PicPay": {"tipo": "dia_util", "dia": 3},
        "Safra": {"tipo": "dia_util", "dia": 3},
        "BRB": {"tipo": "dia_util", "dia": 5},
        "Paraná": {"tipo": "dia_fixo", "dia": 14},
        "BMG": {"tipo": "dia_fixo", "dia": 16},
        "Itaú": {"tipo": "dia_fixo", "dia": 17},
        "BRB360": {"tipo": "dia_fixo", "dia": 25},
        "Crefisa": {"tipo": "dia_fixo", "dia": 28},
        "Banrisul": {"tipo": "dia_fixo", "dia": 29}, 
        "Amigoz": {"tipo": "ultimo_dia"},
        "CBA": {"tipo": "ultimo_dia"},
        "Happy": {"tipo": "ultimo_dia"},
        "Daycoval": {"tipo": "ultimo_dia"},
        "QueroMais": {"tipo": "ultimo_dia"},
        "BTW": {"tipo": "ultimo_dia"},
    }

    try:
        res = supabase.table("notas_fiscais").select("banco, data_emissao, emitida").eq("emitida", True).order("data_emissao", desc=True).execute()
        df_emitidas = pd.DataFrame(res.data)
        
        hoje = date.today()
        cal = calendar.Calendar()
        dias_uteis_mes = [d for d in cal.itermonthdates(hoje.year, hoje.month) if d.month == hoje.month and d.weekday() < 5]
        
        atrasados = []
        vencendo_logo = []

        for banco, regra in REGRAS_ALERTAS.items():
            df_b = df_emitidas[df_emitidas['banco'] == banco]
            ultima = df_b['data_emissao'].max() if not df_b.empty else "2000-01-01"
            ultima = pd.to_datetime(ultima).date()

            # --- Lógica Semanal ---
            if regra["tipo"] == "semanal":
                dias_desde_ultima = (hoje - ultima).days
                if dias_desde_ultima > 7:
                    atrasados.append(f"🚨 **{banco}**: Semanal atrasada há {dias_desde_ultima} dias!")
                elif dias_desde_ultima >= (7 - DIAS_ANTECEDENCIA):
                    vencendo_logo.append(f"⚠️ **{banco}**: Emitir nota semanal até amanhã!")

            # --- Lógica Mensal ---
            else:
                # Calcula data limite
                if regra["tipo"] == "dia_util":
                    dia_alvo = regra["dia"]
                    data_limite = dias_uteis_mes[dia_alvo - 1] if len(dias_uteis_mes) >= dia_alvo else hoje
                elif regra["tipo"] == "dia_fixo":
                    try: data_limite = hoje.replace(day=regra["dia"])
                    except: data_limite = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
                elif regra["tipo"] == "ultimo_dia":
                    data_limite = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

                # VERIFICAÇÃO PROATIVA
                # Se ainda não emitiu no mês atual
                if ultima < hoje.replace(day=1):
                    # Se já passou do prazo
                    if hoje >= data_limite:
                        atrasados.append(f"🚨 **{banco}**: PRAZO ESGOTADO ({data_limite.strftime('%d/%m')})!")
                    # Se está chegando perto (Proativo)
                    elif (data_limite - hoje).days <= DIAS_ANTECEDENCIA:
                        vencendo_logo.append(f"⚠️ **{banco}**: Vence em {(data_limite - hoje).days} dias ({data_limite.strftime('%d/%m')})!")

        # --- EXIBIÇÃO ESTILO "POP-UP" ---
        if atrasados or vencendo_logo:
            # Toast é a notificação que "pula" na tela
            st.toast("Você tem pendências de notas!", icon="⚠️")
            
            st.warning("### 🔔 Central de Alertas Proativos")
            
            if atrasados:
                with st.container():
                    for a in atrasados:
                        st.error(a)
            
            if vencendo_logo:
                with st.container():
                    for v in vencendo_logo:
                        st.info(v)
            st.write("---")

    except:
        pass

exibir_painel_alertas()

# --- 3. FUNÇÃO MESTRA (ABAS) ---
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
                if status_emitida: st.success("🟢 STATUS: EMITIDA")
                else: st.error("🔴 STATUS: NÃO EMITIDA")
            
            if st.form_submit_button("💾 Salvar"):
                if not num_nf: st.warning("⚠️ Preencha o número da Nota.")
                elif categoria == "Auto (C6)" and "C6" not in banco: st.error("⛔ Erro: Auto é para C6.")
                else:
                    ref_formatada = data_ref_input.strftime("%m/%Y")
                    dados = {"codigo": codigo_atual, "banco": banco, "categoria": categoria, "referencia": ref_formatada, "data_emissao": str(data_em), "numero_nf": num_nf, "emitida": status_emitida}
                    try:
                        supabase.table("notas_fiscais").insert(dados).execute()
                        st.success(f"✅ Salvo!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"❌ Erro: {e}")

    with st.expander("🗑️ Excluir Nota Errada"):
        try:
            res_delete = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("id", desc=True).limit(30).execute()
            if res_delete.data:
                opcoes_exclusao = {f"NF {item['numero_nf']} ({item.get('referencia', '-')}) - {item['banco']}": item['id'] for item in res_delete.data}
                nota_selecionada = st.selectbox("Selecione:", list(opcoes_exclusao.keys()), key=f"sel_del_{codigo_atual}")
                if st.button(f"Apagar Nota", type="primary", key=f"btn_del_{codigo_atual}"):
                    supabase.table("notas_fiscais").delete().eq("id", opcoes_exclusao[nota_selecionada]).execute()
                    st.toast("🗑️ Apagado!")
                    time.sleep(1); st.rerun()
        except: st.caption("Lista vazia.")

    st.write("---")
    try:
        response = supabase.table("notas_fiscais").select("*").eq("codigo", codigo_atual).order("data_emissao", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['data_emissao'] = pd.to_datetime(df['data_emissao'])
            df['STATUS'] = df['emitida'].apply(lambda x: "🟢 Emitida" if x else "🔴 Pendente")
            df['ano'] = df['data_emissao'].dt.year
            df['mes_num'] = df['data_emissao'].dt.month
            grupos = df.groupby(['ano', 'mes_num'])
            for (ano, mes_num), dados_mes in sorted(grupos, key=lambda x: (x[0][0], x[0][1]), reverse=True):
                with st.expander(f"Mês {mes_num}/{ano} — ({len(dados_mes)} notas)"):
                    cols_final = [c for c in ['STATUS', 'referencia', 'banco', 'categoria', 'numero_nf', 'data_emissao'] if c in df.columns]
                    st.dataframe(dados_mes[cols_final], hide_index=True, use_container_width=True)
    except: st.error("Erro ao carregar dados.")

tab1, tab2, tab3 = st.tabs(["Código TN", "Código TL", "Código JF"])
with tab1: desenhar_aba_codigo("TN")
with tab2: desenhar_aba_codigo("TL")
with tab3: desenhar_aba_codigo("JF")
