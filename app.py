import streamlit as st
import pandas as pd
import time
import calendar
from datetime import date, timedelta, datetime
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO VISUAL ---
try:
    st.set_page_config(page_title="Controle de Notas", page_icon="logo.png", layout="wide")
except:
    st.set_page_config(page_title="Controle de Notas", page_icon="📝", layout="wide")

# ==========================================
# --- SISTEMA DE LOGIN E SEGURANÇA ---
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_logado = ""
    st.session_state.is_admin = False

if not st.session_state.autenticado:
    col_v1, col_login, col_v2 = st.columns([1, 2, 1])
    with col_login:
        st.title("🔒 Acesso Restrito")
        with st.form("login"):
            u = st.text_input("Usuário").lower().strip()
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                users = st.secrets.get("usuarios", {})
                if u in users and users[u] == s:
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = u.capitalize()
                    st.session_state.is_admin = (u == "admin")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")
    st.stop()

# --- CABEÇALHO ---
col_l, col_t, col_u = st.columns([1, 7, 2])
with col_l:
    try: st.image("logo.png", width=80)
    except: pass
with col_t:
    st.title(f"Controle de Notas Fiscais")
with col_u:
    st.write(f"👤 **{st.session_state.usuario_logado}**")
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

# --- CONEXÃO ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ==========================================
# --- REGRAS E BANCOS ---
# ==========================================
LISTAS_BANCOS = {
    "TN": ["AgiBank", "Banrisul", "BMG", "BOC", "C6 Bank", "Cetelem", "CredFranco", "Crefaz", "Daycoval", "Digio", "Diga", "Facta", "Itaú", "Master", "Pan", "Paraná", "PresençaBank", "Santander", "PicPay", "Voce Seguradora", "QueroMais", "TeddyHub"],
    "TL": ["Amigoz", "Banrisul", "Banco do Brasil", "BMG", "BRB", "BTW", "CBA", "C6 Bank", "Capital", "CredFranco", "Crefisa", "Digio", "Facta", "Futuro Previdência", "GVN", "Happy", "iCred", "Itaú", "Lecca", "Nossa Fintech", "Pan", "Santander", "ZiliCred", "Safra"],
    "JF": ["Daycoval", "Santander"]
}

REGRAS = {
    "AgiBank": {"tipo": "dia_util", "dia": 1}, "Capital": {"tipo": "semanal", "dias": 7},
    "Amigoz": {"tipo": "dia_fixo", "dia": 1}, "Banrisul": {"tipo": "dia_fixo", "dia": 29},
    "Banco do Brasil": {"tipo": "dia_util", "dia": 3}, "BMG": {"tipo": "dia_fixo", "dia": 16},
    "BRB": {"tipo": "dia_util", "dia": 5}, "C6 Bank": {"tipo": "dia_util", "dia": 1},
    "CBA": {"tipo": "dia_fixo", "dia": 1}, "CCB": {"tipo": "dia_util", "dia": 1},
    "Crefaz": {"tipo": "semanal", "dias": 7}, "Crefisa": {"tipo": "dia_fixo", "dia": 28},
    "Daycoval": {"tipo": "ultimo_dia"}, "Digio": {"tipo": "dia_util", "dia": 3},
    "Happy": {"tipo": "dia_fixo", "dia": 1}, "iCred": {"tipo": "dia_util", "dia": 3},
    "Itaú": {"tipo": "dia_fixo", "dia": 17}, "Mercantil TL": {"tipo": "dia_util", "dia": 1},
    "Mercantil CP": {"tipo": "semanal", "dias": 7}, "Pan": {"tipo": "dia_util", "dia": 3},
    "Paraná": {"tipo": "dia_fixo", "dia": 14}, "PicPay": {"tipo": "dia_util", "dia": 3},
    "PresençaBank": {"tipo": "dia_util", "dia": 1}, "Santander": {"tipo": "semanal", "dias": 7},
    "BTW": {"tipo": "dia_fixo", "dia": 1}, "BRB360": {"tipo": "dia_fixo", "dia": 25},
    "Safra": {"tipo": "dia_util", "dia": 3}, "QueroMais": {"tipo": "ultimo_dia"}
}

# ==========================================
# --- LÓGICA DE COBRANÇA (DIREITA) ---
# ==========================================
def exibir_cobrancas(codigo):
    hoje = date.today()
    DATA_INICIO = date(2026, 4, 25)
    res = supabase.table("notas_fiscais").select("banco, data_emissao, emitida").eq("codigo", codigo).eq("emitida", True).eq("ativo", True).execute()
    df_e = pd.DataFrame(res.data)
    
    atrasados, urgentes = [], []
    for banco in LISTAS_BANCOS[codigo]:
        if banco not in REGRAS: continue
        r = REGRAS[banco]
        ultima = pd.to_datetime(df_e[df_e['banco']==banco]['data_emissao'].max()).date() if not df_e.empty and banco in df_e['banco'].values else None
        
        # Simplificação da data limite (dia útil/fixo)
        if r["tipo"] == "dia_util": limite = hoje.replace(day=r["dia"]) # Simplificado para exemplo
        elif r["tipo"] == "dia_fixo": limite = hoje.replace(day=min(r["dia"], 28))
        else: limite = hoje.replace(day=28)

        if limite < DATA_INICIO: continue
        emitida_mes = ultima and ultima >= hoje.replace(day=1)
        
        if not emitida_mes:
            if hoje > limite: atrasados.append(f"🚨 {banco} (Venceu {limite.strftime('%d/%m')})")
            elif (limite - hoje).days <= 2: urgentes.append(f"⚠️ {banco} (Vence em {(limite-hoje).days} dias)")

    st.subheader(f"📢 Cobranças {codigo}")
    if atrasados:
        st.error("🚩 **ATRASADOS**")
        for a in atrasados: st.write(a)
    if urgentes:
        st.warning("⏳ **URGENTES**")
        for u in urgentes: st.write(u)
    if not atrasados and not urgentes: st.success("✅ Tudo em dia!")

# ==========================================
# --- LANÇAMENTOS E AÇÃO EM LOTE (ESQUERDA) ---
# ==========================================
def desenhar_painel(codigo):
    col_f, col_c = st.columns([7, 3], gap="large")
    
    with col_f:
        # --- LANÇAR ---
        with st.expander("➕ Nova Nota", expanded=True):
            with st.form(f"f_{codigo}"):
                c1, c2 = st.columns(2)
                with c1:
                    b = st.selectbox("Banco", LISTAS_BANCOS[codigo])
                    cat = st.selectbox("Tipo", ["Comissão a Vista", "Pro-Rata", "Campanha", "Seguro", "Auto (C6)"])
                    d = st.date_input("Emissão")
                with c2:
                    n = st.text_input("Número NF")
                    ref = st.date_input("Referência")
                    st.write("---")
                    e = st.toggle("Emitida", value=True)
                if st.form_submit_button("Salvar", use_container_width=True):
                    supabase.table("notas_fiscais").insert({"codigo":codigo, "banco":b, "categoria":cat, "data_emissao":str(d), "numero_nf":n, "referencia":ref.strftime("%m/%Y"), "emitida":e, "criado_por":st.session_state.usuario_logado}).execute()
                    st.success("Salvo!"); time.sleep(1); st.rerun()

        # --- AÇÃO EM LOTE E HISTÓRICO ---
        st.write("---")
        st.subheader("📂 Histórico e Ações em Lote")
        busca = st.text_input("🔍 Buscar por Banco, NF ou Mês/Ano")
        
        res = supabase.table("notas_fiscais").select("*").eq("codigo", codigo).eq("ativo", True).order("data_emissao", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            if busca:
                df = df[df.apply(lambda row: busca.lower() in str(row).lower(), axis=1)]

            # Ação em Lote usando st.data_editor
            st.info("💡 Para dar baixa em lote: Marque a coluna 'EMITIDA' e clique em 'Salvar Alterações'.")
            df_view = df[['id', 'emitida', 'numero_nf', 'banco', 'referencia', 'data_emissao', 'criado_por']]
            
            # O data_editor permite editar a coluna 'emitida' em várias linhas de uma vez
            edited_df = st.data_editor(
                df_view, 
                column_config={"emitida": st.column_config.CheckboxColumn("EMITIDA"), "id": None}, # Esconde ID
                disabled=["numero_nf", "banco", "referencia", "data_emissao", "criado_por"],
                use_container_width=True,
                hide_index=True,
                key=f"editor_{codigo}"
            )

            if st.button("✔️ Salvar Alterações em Lote", key=f"btn_lote_{codigo}"):
                # Compara o original com o editado e atualiza o banco
                for i, row in edited_df.iterrows():
                    id_nota = row['id']
                    novo_status = row['emitida']
                    # Só atualiza se mudou
                    if novo_status != df.loc[df['id']==id_nota, 'emitida'].values[0]:
                        supabase.table("notas_fiscais").update({"emitida": novo_status, "modificado_por": st.session_state.usuario_logado}).eq("id", id_nota).execute()
                st.success("Alterações salvas!")
                time.sleep(1); st.rerun()

        # --- PAINEL DO ADMIN (LIXEIRA) ---
        if st.session_state.is_admin:
            with st.expander("🛡️ Painel do Chefe (Lixeira)"):
                res_lixo = supabase.table("notas_fiscais").select("*").eq("codigo", codigo).eq("ativo", False).execute()
                if res_lixo.data:
                    df_lixo = pd.DataFrame(res_lixo.data)
                    nota_r = st.selectbox("Restaurar:", df_lixo['numero_nf'] + " - " + df_lixo['banco'])
                    if st.button("♻️ Restaurar Selecionada"):
                        id_r = df_lixo.iloc[st.session_state.index_lixo]['id'] # Lógica simplificada
                        supabase.table("notas_fiscais").update({"ativo": True}).eq("id", id_r).execute()
                        st.rerun()
                else: st.caption("Lixeira vazia.")
                
                if not df.empty:
                    nota_d = st.selectbox("Enviar para Lixeira:", df['numero_nf'] + " - " + df['banco'])
                    if st.button("🗑️ Excluir Nota"):
                        id_d = df[df['numero_nf'] == nota_d.split(" - ")[0]]['id'].values[0]
                        supabase.table("notas_fiscais").update({"ativo": False}).eq("id", id_d).execute()
                        st.rerun()

    with col_c:
        with st.container(border=True):
            exibir_cobrancas(codigo)

# --- ABAS ---
t1, t2, t3 = st.tabs(["Código TN", "Código TL", "Código JF"])
with t1: desenhar_painel("TN")
with t2: desenhar_painel("TL")
with t3: desenhar_painel("JF")
