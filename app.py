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
        st.write("")
        st.write("")
        try: st.image("logo.png", width=150)
        except: pass
        st.title("🔒 Login do Sistema")
        
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
    st.title("Controle de Notas Fiscais")
with col_u:
    st.write(f"👤 **{st.session_state.usuario_logado}**")
    if st.button("Sair", key="btn_sair_global"):
        st.session_state.autenticado = False
        st.rerun()

# --- CONEXÃO ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("⚠️ Erro de Conexão. Verifique os Secrets.")
    st.stop()

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
    
    try:
        res = supabase.table("notas_fiscais").select("banco, data_emissao, emitida").eq("codigo", codigo).eq("emitida", True).eq("ativo", True).execute()
        df_e = pd.DataFrame(res.data)
        
        atrasados, urgentes = [], []
        for banco in LISTAS_BANCOS.get(codigo, []):
            if banco not in REGRAS: continue
            r = REGRAS[banco]
            
            ultima = None
            if not df_e.empty and banco in df_e['banco'].values:
                ultima = pd.to_datetime(df_e[df_e['banco']==banco]['data_emissao'].max()).date()
            
            if r["tipo"] == "dia_util": limite = hoje.replace(day=r["dia"]) 
            elif r["tipo"] == "dia_fixo": 
                try: limite = hoje.replace(day=r["dia"])
                except: limite = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
            else: 
                limite = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

            if limite < DATA_INICIO: continue
            
            emitida_mes = ultima and ultima >= hoje.replace(day=1)
            
            if not emitida_mes:
                if hoje > limite: atrasados.append(f"🚨 {banco} (Venceu {limite.strftime('%d/%m')})")
                elif (limite - hoje).days <= 2: urgentes.append(f"⚠️ {banco} (Vence em {(limite-hoje).days} dias)")

        st.subheader(f"📢 Cobranças: {codigo}")
        if atrasados:
            st.error("🚩 **ATRASADOS**")
            for a in atrasados: st.write(a)
        if urgentes:
            st.warning("⏳ **URGENTES**")
            for u in urgentes: st.write(u)
        if not atrasados and not urgentes: st.success("✅ Tudo em dia!")
        
    except Exception as e:
        st.caption("Aguardando dados...")

# ==========================================
# --- LANÇAMENTOS, EDIÇÃO E AÇÃO EM LOTE ---
# ==========================================
def desenhar_painel(codigo):
    col_f, col_c = st.columns([7, 3], gap="large")
    
    with col_f:
        # --- 1. LANÇAR NOVA NOTA ---
        with st.expander("➕ Nova Nota", expanded=True):
            with st.form(f"f_lancamento_{codigo}", clear_on_submit=False):
                c1, c2 = st.columns(2)
                with c1:
                    b = st.selectbox("Banco", LISTAS_BANCOS.get(codigo, ["Outros"]), key=f"banco_lan_{codigo}")
                    cat = st.selectbox("Tipo", ["Comissão a Vista", "Pro-Rata", "Campanha", "Seguro", "Auto (C6)"], key=f"cat_lan_{codigo}")
                    d = st.date_input("Emissão", key=f"data_lan_{codigo}")
                with c2:
                    n = st.text_input("Número NF", key=f"nf_lan_{codigo}")
                    ref = st.date_input("Referência", key=f"ref_lan_{codigo}")
                    st.write("---")
                    e = st.toggle("Emitida", value=True, key=f"tgl_lan_{codigo}")
                if st.form_submit_button("Salvar", use_container_width=True):
                    if not n: st.warning("⚠️ Preencha a NF.")
                    else:
                        supabase.table("notas_fiscais").insert({"codigo":codigo, "banco":b, "categoria":cat, "data_emissao":str(d), "numero_nf":n, "referencia":ref.strftime("%m/%Y"), "emitida":e, "criado_por":st.session_state.usuario_logado}).execute()
                        st.success("Salvo!"); time.sleep(1); st.rerun()

        # --- 2. ÁREA DE EDIÇÃO (CORRIGIR DADOS) ---
        with st.expander("✏️ Editar Detalhes da Nota Existente"):
            try:
                res_edit = supabase.table("notas_fiscais").select("*").eq("codigo", codigo).eq("ativo", True).order("id", desc=True).limit(50).execute()
                if res_edit.data:
                    dados_map = {item['id']: item for item in res_edit.data}
                    opcoes_display = {f"NF {item['numero_nf']} ({item.get('referencia', '-')}) - {item['banco']}": item['id'] for item in res_edit.data}
                    
                    nota_selecionada = st.selectbox("Selecione a nota que deseja corrigir:", ["Selecione..."] + list(opcoes_display.keys()), key=f"sel_edit_{codigo}")
                    
                    if nota_selecionada != "Selecione...":
                        id_real = opcoes_display[nota_selecionada]
                        nota_atual = dados_map[id_real]
                        
                        st.info("Altere os dados abaixo e clique em 'Atualizar'.")
                        with st.form(f"form_edit_real_{codigo}"):
                            c_edit1, c_edit2 = st.columns(2)
                            
                            opcoes_bancos = LISTAS_BANCOS.get(codigo, ["Outros"])
                            idx_banco = opcoes_bancos.index(nota_atual['banco']) if nota_atual['banco'] in opcoes_bancos else 0
                            
                            lista_categorias = ["Comissão a Vista", "Pro-Rata", "Campanha", "Seguro", "Auto (C6)"]
                            idx_cat = lista_categorias.index(nota_atual.get('categoria', 'Comissão a Vista')) if nota_atual.get('categoria') in lista_categorias else 0
                            
                            try: data_db = datetime.strptime(nota_atual['data_emissao'], "%Y-%m-%d").date()
                            except: data_db = date.today()

                            with c_edit1:
                                novo_banco = st.selectbox("Banco", options=opcoes_bancos, index=idx_banco)
                                nova_cat = st.selectbox("Tipo", options=lista_categorias, index=idx_cat)
                                nova_data = st.date_input("Data de Emissão", value=data_db)
                            
                            with c_edit2:
                                novo_num = st.text_input("Número da NF", value=nota_atual['numero_nf'])
                                nova_ref = st.text_input("Mês/Ano Referência", value=nota_atual.get('referencia', ''))
                                novo_status = st.toggle("Emitida", value=nota_atual['emitida'])
                                
                            if st.form_submit_button("🔄 Atualizar Lançamento", type="primary", use_container_width=True):
                                dados_atualizados = {
                                    "banco": novo_banco, "categoria": nova_cat, 
                                    "referencia": nova_ref, "data_emissao": str(nova_data), 
                                    "numero_nf": novo_num, "emitida": novo_status,
                                    "modificado_por": st.session_state.usuario_logado
                                }
                                supabase.table("notas_fiscais").update(dados_atualizados).eq("id", id_real).execute()
                                st.success("Nota atualizada com sucesso!")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.caption("Nenhuma nota recente para editar.")
            except Exception as e:
                st.caption(f"Erro ao carregar edição: {e}")

        # --- 3. AÇÃO EM LOTE E HISTÓRICO ---
        st.write("---")
        st.subheader("📂 Histórico e Ações em Lote")
        busca = st.text_input("🔍 Buscar por Banco, NF ou Mês/Ano (Aperte Enter para filtrar)", key=f"busca_{codigo}")
        
        try:
            res = supabase.table("notas_fiscais").select("*").eq("codigo", codigo).eq("ativo", True).order("data_emissao", desc=True).limit(500).execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                if busca:
                    df = df[df.apply(lambda row: busca.lower() in str(row).lower(), axis=1)]

                st.info("💡 Para dar baixa em lote: Marque a coluna 'EMITIDA' e clique em 'Salvar Alterações'.")
                df_view = df[['id', 'emitida', 'numero_nf', 'banco', 'referencia', 'data_emissao', 'criado_por']]
                
                edited_df = st.data_editor(
                    df_view, 
                    column_config={"emitida": st.column_config.CheckboxColumn("EMITIDA"), "id": None}, 
                    disabled=["numero_nf", "banco", "referencia", "data_emissao", "criado_por"],
                    use_container_width=True,
                    hide_index=True,
                    key=f"editor_tabela_{codigo}"
                )

                if st.button("✔️ Salvar Alterações em Lote", key=f"btn_lote_{codigo}"):
                    for i, row in edited_df.iterrows():
                        id_nota = row['id']
                        novo_status = row['emitida']
                        status_antigo = df.loc[df['id']==id_nota, 'emitida'].values[0]
                        if novo_status != status_antigo:
                            supabase.table("notas_fiscais").update({"emitida": novo_status, "modificado_por": st.session_state.usuario_logado}).eq("id", id_nota).execute()
                    st.success("Alterações salvas!")
                    time.sleep(1); st.rerun()
            else:
                st.caption("Nenhum histórico encontrado.")
        except Exception as e:
            st.error("Erro ao carregar o histórico.")

        # --- 4. PAINEL DE EXCLUSÃO (LIXEIRA LIBERADA PARA TODOS) ---
        with st.expander("🗑️ Lixeira (Ocultar ou Restaurar Notas)"):
            col_lixo1, col_lixo2 = st.columns(2)
            
            with col_lixo1:
                st.markdown("**Enviar para a Lixeira**")
                try:
                    res_ativas = supabase.table("notas_fiscais").select("id, numero_nf, banco, data_emissao").eq("codigo", codigo).eq("ativo", True).order("id", desc=True).limit(100).execute()
                    if res_ativas.data:
                        opcoes_del = {f"NF {item['numero_nf']} - {item['banco']} ({item['data_emissao']})": item['id'] for item in res_ativas.data}
                        nota_apagar = st.selectbox("Selecione a nota:", list(opcoes_del.keys()), key=f"sel_del_{codigo}")
                        if st.button("🚨 Apagar (Ocultar)", type="primary", use_container_width=True, key=f"btn_del_confirma_{codigo}"):
                            id_para_apagar = opcoes_del[nota_apagar]
                            supabase.table("notas_fiscais").update({"ativo": False, "modificado_por": st.session_state.usuario_logado}).eq("id", id_para_apagar).execute()
                            st.toast("Enviada para lixeira!")
                            time.sleep(1); st.rerun()
                    else: st.caption("Não há notas para apagar.")
                except: pass
            
            with col_lixo2:
                st.markdown("**Restaurar da Lixeira**")
                try:
                    res_lixo = supabase.table("notas_fiscais").select("id, numero_nf, banco, data_emissao").eq("codigo", codigo).eq("ativo", False).order("id", desc=True).execute()
                    if res_lixo.data:
                        opcoes_res = {f"NF {item['numero_nf']} - {item['banco']} ({item['data_emissao']})": item['id'] for item in res_lixo.data}
                        nota_restaurar = st.selectbox("Selecione a nota:", list(opcoes_res.keys()), key=f"sel_res_{codigo}")
                        if st.button("♻️ Restaurar Nota", type="secondary", use_container_width=True, key=f"btn_res_confirma_{codigo}"):
                            id_para_restaurar = opcoes_res[nota_restaurar]
                            supabase.table("notas_fiscais").update({"ativo": True, "modificado_por": st.session_state.usuario_logado}).eq("id", id_para_restaurar).execute()
                            st.toast("Restaurada!")
                            time.sleep(1); st.rerun()
                    else: st.caption("A lixeira está vazia.")
                except: pass

    with col_c:
        with st.container(border=True):
            exibir_cobrancas(codigo)

# --- ABAS ---
t1, t2, t3 = st.tabs(["Código TN", "Código TL", "Código JF"])
with t1: desenhar_painel("TN")
with t2: desenhar_painel("TL")
with t3: desenhar_painel("JF")
