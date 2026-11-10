"""Aceiro: boletim de fogo e seca para a agricultura familiar do Pará (protótipo em Streamlit).

Quatro páginas:
- Início: o que é o Aceiro, em 30 segundos, e como usar o painel.
- Visão do agricultor: o boletim como chega no celular, em cada canal.
- Painel do técnico: mapa por nível, fila de revisão, boletim e tendência.
- Sobre os dados: fontes, regra de demonstração e limites.

Os focos e o cadastro são dados reais. O nível usa uma regra de demonstração
(a mesma de sql/03_gerar_boletins.sql), não o score do modelo.

Uso (na raiz do repositório):
    python app/preparar_dados.py
    streamlit run app/painel.py
"""

import copy
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))  # para achar regras.py em qualquer forma de rodar
from regras import NIVEIS, acao, texto_sms  # noqa: E402

DADOS = PASTA / "dados"
CORES = {  # do mais claro ao mais escuro, para o nível ser lido mesmo sem distinguir cor
    "verde": "#3E9B63",
    "amarelo": "#EBC944",
    "laranja": "#E8772E",
    "vermelho": "#B23A2E",
}
SIMBOLO = (PASTA / "aceiro-simbolo.svg").read_text(encoding="utf-8")
CANAL = {"radio": "Rádio comunitário e visita do técnico", "whatsapp": "WhatsApp (texto e áudio)"}
SIGNIFICADO = {
    "verde": "Sem alerta no município nesta semana.",
    "amarelo": "Atenção: há algum foco de calor no município ou o período é de risco.",
    "laranja": "Alerta: muitos focos de calor no município nesta semana.",
    "vermelho": "Alerta máximo: fogo muito ativo no município nesta semana.",
}

ESTILO = """
<style>
#MainMenu, header [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none;}
.block-container {padding-top: 3.4rem; padding-bottom: 2rem; max-width: 1400px;}
.ac-topo {display: flex; align-items: center; gap: 14px; margin-bottom: .2rem;}
.ac-topo svg {width: 52px; height: 52px; flex: none;}
.ac-topo .ac-h1 {font-size: 1.9rem; line-height: 1.1; margin: 0; padding: 0; font-weight: 700; color: #1E2A4A;}
.ac-topo p {margin: 2px 0 0; color: #5B6478; font-size: .95rem;}
.ac-aviso {border-left: 5px solid #E8590C; background: #FDF0E6; padding: 12px 16px; border-radius: 6px;
           margin: .9rem 0 1.1rem; color: #4A2A12; font-size: .95rem;}
.ac-aviso b {color: #B4460A;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #E6DED0; border-radius: 10px; padding: 14px 18px;}
[data-testid="stMetricLabel"] p {font-size: .85rem; color: #5B6478;}
[data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700;}
.stTabs [data-baseweb="tab"] {font-weight: 600;}
.ac-legenda {display: flex; flex-wrap: wrap; gap: 14px; font-size: .9rem; color: #1E2A4A; margin-top: 6px;}
.ac-legenda span.ac-pt {display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px;}
section[data-testid="stSidebar"] .ac-marca {display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.25rem;}
section[data-testid="stSidebar"] .ac-marca svg {width: 34px; height: 34px;}

/* Início */
.ac-hero {display: flex; align-items: center; gap: 22px; margin: .4rem 0 1.2rem;}
.ac-hero svg {width: 84px; height: 84px; flex: none;}
.ac-hero h1 {font-size: 2.6rem; margin: 0; padding: 0; color: #1E2A4A;}
.ac-hero p {font-size: 1.15rem; color: #4A5568; margin: 4px 0 0;}
.ac-cartoes {display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin: .6rem 0 1rem;}
.ac-cartao {background: #FFFFFF; border: 1px solid #E6DED0; border-radius: 12px; padding: 16px 18px;}
.ac-cartao .ac-rot {font-size: .78rem; font-weight: 700; letter-spacing: .06em; color: #2F8F4E; text-transform: uppercase;}
.ac-cartao h4 {margin: 4px 0 6px; padding: 0; color: #1E2A4A; font-size: 1.08rem;}
.ac-cartao p {margin: 0; color: #4A5568; font-size: .95rem; line-height: 1.45;}
.ac-numero {font-size: 2rem; font-weight: 800; color: #1E2A4A; line-height: 1.1;}
.ac-rodape {margin-top: 2rem; padding-top: .8rem; border-top: 1px solid #E6DED0; color: #5B6478; font-size: .85rem;}

/* Visão do agricultor: celular */
.ac-celular {max-width: 360px; margin: 0 auto; border: 10px solid #1E2A4A; border-radius: 34px;
             background: #ECE5DD; overflow: hidden; box-shadow: 0 6px 18px rgba(30,42,74,.18);}
.ac-cel-topo {background: #2F8F4E; color: #FFFFFF; padding: 12px 16px; font-weight: 700; display: flex; align-items: center; gap: 10px;}
.ac-cel-topo svg {width: 28px; height: 28px; background: #FFFFFF; border-radius: 50%; padding: 2px;}
.ac-cel-topo small {display: block; font-weight: 400; opacity: .85; font-size: .78rem;}
.ac-cel-corpo {padding: 14px 12px 18px; min-height: 380px;}
.ac-balao {background: #FFFFFF; border-radius: 4px 12px 12px 12px; padding: 10px 12px; margin-bottom: 10px;
           color: #1E2A4A; font-size: .95rem; line-height: 1.45; box-shadow: 0 1px 1px rgba(0,0,0,.08);}
.ac-balao .ac-hora {display: block; text-align: right; color: #8A94A6; font-size: .72rem; margin-top: 4px;}
.ac-audio {display: flex; align-items: center; gap: 10px;}
.ac-audio .ac-play {width: 30px; height: 30px; border-radius: 50%; background: #2F8F4E; color: #FFF;
                    display: flex; align-items: center; justify-content: center; font-size: .8rem;}
.ac-audio .ac-onda {flex: 1; height: 4px; background: repeating-linear-gradient(90deg, #2F8F4E 0 3px, transparent 3px 6px); border-radius: 2px;}
.ac-sms {font-family: ui-monospace, Menlo, monospace; font-size: .9rem; background: #FFFFFF; border-radius: 12px;
         padding: 12px 14px; border: 1px solid #E6DED0; color: #1E2A4A;}
</style>
"""

st.set_page_config(page_title="Aceiro · Boletim de fogo e seca", page_icon="🔥", layout="wide")
st.markdown(ESTILO, unsafe_allow_html=True)


# ---------------------------------------------------------------- dados
@st.cache_data
def carregar(versao):
    """`versao` é a data de modificação do CSV: se o arquivo mudar, o cache é refeito."""
    if versao is None:
        return None, None
    bol = pd.read_csv(DADOS / "boletins_semana.csv", dtype={"cod_municipio": str}, parse_dates=["inicio_semana"])
    malha = json.loads((DADOS / "municipios.geojson").read_text(encoding="utf-8"))
    return bol, malha


def rgb(hexa, alfa=210):
    hexa = hexa.lstrip("#")
    return [int(hexa[i:i + 2], 16) for i in (0, 2, 4)] + [alfa]


def selo(nivel):
    cor = CORES[nivel]
    texto = "#FFFFFF" if nivel in ("vermelho", "verde", "laranja") else "#1E2A4A"
    return (f"<span style='background:{cor};color:{texto};padding:3px 12px;border-radius:12px;"
            f"font-weight:700;font-size:0.85rem'>{nivel.upper()}</span>")


def motivo(linha):
    texto = f"{linha.qtd_focos} focos de calor no município nesta semana"
    if pd.notna(linha.dias_sem_chuva_mediana):
        texto += f" e {int(linha.dias_sem_chuva_mediana)} dias sem chuva (mediana dos focos)"
    return texto + "."


def texto_whatsapp(linha, aviso):
    partes = []
    if aviso:
        partes.append("Período de alto risco de fogo no Pará.")
    partes.append(motivo(linha))
    partes.append(f"**O que fazer:** {linha.acao_final}")
    partes.append("_Aviso automático, pode errar. Para sair: SAIR._")
    return "\n\n".join(partes)


def texto_radio(linha):
    return (f"Atenção, agricultor de {linha.nm_municipio}: o nível de alerta de fogo nesta semana é "
            f"{linha.nivel_final}. Foram {linha.qtd_focos} focos de calor no município. "
            f"{linha.acao_final} O aviso é automático e pode errar. Dúvidas? Procure a Emater.")


_csv = DADOS / "boletins_semana.csv"
bol, malha = carregar(_csv.stat().st_mtime if _csv.exists() else None)
if bol is None:
    st.error("Faltam os dados do painel. Rode `python app/preparar_dados.py` na raiz do repositório.")
    st.stop()

if "decisoes" not in st.session_state:
    st.session_state.decisoes = []

# ---------------------------------------------------------------- barra lateral (vale para todas as páginas)
semanas = sorted(bol["semana_ref"].unique())
st.sidebar.markdown(f"<div class='ac-marca'>{SIMBOLO}<span>Aceiro</span></div>", unsafe_allow_html=True)
st.sidebar.caption("Boletim de fogo e seca · protótipo")
semana = st.sidebar.selectbox("Semana do boletim", semanas, index=len(semanas) - 1,
                              format_func=lambda s: f"{s} (a partir de {bol.loc[bol.semana_ref == s, 'inicio_semana'].iloc[0]:%d/%m})")
st.sidebar.caption(
    "Dados reais: focos do INPE (satélite de referência), IBGE, Anatel e NOAA, de ago. a out./2026. "
    "O nível usa uma regra de demonstração, não o score do modelo."
)
if semana in ("2026-W31", "2026-W44"):
    st.sidebar.warning("Semana incompleta: os dados vão de 01/08 a 31/10.")

atual = bol[bol["semana_ref"] == semana].copy()
pos = semanas.index(semana)
anterior = bol[bol["semana_ref"] == semanas[pos - 1]] if pos > 0 else None
aviso = atual["fl_aviso_periodo"].iloc[0] == "S"
inicio = atual["inicio_semana"].iloc[0]

# Decisões do técnico nesta sessão (simulação: nada é enviado)
for d in st.session_state.decisoes:
    if d["semana"] == semana:
        atual.loc[atual["cod_municipio"] == d["cod_municipio"], "nivel_final"] = d["nivel_final"]
atual["nivel_final"] = atual.get("nivel_final", pd.Series(index=atual.index, dtype=object)).fillna(atual["nivel_alerta"])
# Ação e textos de todos os canais saem do nível final, depois da decisão do técnico
atual["acao_final"] = atual["nivel_final"].map(acao)
atual["sms_final"] = [texto_sms(n, q) for n, q in zip(atual["nivel_final"], atual["qtd_focos"])]
atual["ajustado"] = atual["nivel_final"] != atual["nivel_alerta"]
nomes_por_focos = atual.sort_values("qtd_focos", ascending=False)["nm_municipio"].tolist()


def rodape():
    st.markdown(
        "<div class='ac-rodape'>Aceiro · Grupo Raiz de Dados (Gustavo de Araujo Barbosa e Jonatas Menezes da Silva) · "
        "FIAP, Global Solution 2026/2, CitizenTech · Protótipo acadêmico: não envia mensagens reais.</div>",
        unsafe_allow_html=True)


# ================================================================ páginas
def pagina_inicio():
    total_focos = int(bol["qtd_focos"].sum())
    familiar = int(bol.drop_duplicates("cod_municipio")["qtd_estab_agro_familiar"].sum())
    fmt = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
    st.markdown(
        f"<div class='ac-hero'>{SIMBOLO}<div><h1>Aceiro</h1>"
        "<p>Boletim semanal de fogo e seca, em linguagem simples, para a agricultura familiar do Pará.</p></div></div>",
        unsafe_allow_html=True)

    st.markdown(f"""
<div class='ac-cartoes'>
  <div class='ac-cartao'><div class='ac-rot'>O problema</div><h4>O dado existe, a decisão não chega</h4>
    <p>Focos de fogo, seca e El Niño são públicos, mas chegam em mapas e índices técnicos.
    Quem vive da roça precisa saber o que fazer nesta semana.</p></div>
  <div class='ac-cartao'><div class='ac-rot'>A solução</div><h4>Um boletim por município, toda semana</h4>
    <p>Nível de alerta, o motivo em uma frase e a ação da semana, como abrir o aceiro.
    Chega por WhatsApp, SMS, rádio comunitário ou visita do técnico da Emater.</p></div>
  <div class='ac-cartao'><div class='ac-rot'>Quem decide</div><h4>O técnico revisa antes de sair</h4>
    <p>Alerta vermelho só sai depois da revisão do técnico. Para baixar o nível, ele precisa
    registrar o motivo.</p></div>
</div>
<div class='ac-cartoes'>
  <div class='ac-cartao'><div class='ac-numero'>{fmt(total_focos)}</div>
    <p>focos de calor no Pará de ago. a out./2026 (INPE, satélite de referência)</p></div>
  <div class='ac-cartao'><div class='ac-numero'>144</div>
    <p>municípios com boletim toda semana</p></div>
  <div class='ac-cartao'><div class='ac-numero'>{fmt(familiar)}</div>
    <p>estabelecimentos da agricultura familiar no estado (IBGE, Censo Agro 2017)</p></div>
</div>
""", unsafe_allow_html=True)

    st.subheader("Como usar este protótipo")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. Veja o que o agricultor recebe**")
        st.caption("Escolha um município e veja o boletim no WhatsApp, no SMS e no rádio.")
        st.page_link(PAGINAS["agricultor"], label="Abrir a visão do agricultor", icon="📱")
    with c2:
        st.markdown("**2. Faça o papel do técnico**")
        st.caption("Veja o mapa da semana e revise os alertas vermelhos na fila.")
        st.page_link(PAGINAS["tecnico"], label="Abrir o painel do técnico", icon="🗺️")
    with c3:
        st.markdown("**3. Entenda os dados**")
        st.caption("Fontes, a regra usada para o nível e o que o Aceiro não promete.")
        st.page_link(PAGINAS["dados"], label="Abrir sobre os dados", icon="ℹ️")

    st.info("**O que é real e o que é demonstração.** Os focos, os municípios, a cobertura 4G e o El Niño são "
            "dados públicos reais. O nível de alerta usa uma regra simples de demonstração, e a revisão do "
            "técnico é simulada: nada é gravado nem enviado. As ações ainda precisam de revisão técnica da Emater.")
    rodape()


def pagina_agricultor():
    st.markdown(
        f"<div class='ac-topo'>{SIMBOLO}<div><div class='ac-h1'>Visão do agricultor</div>"
        f"<p>O boletim da semana {semana}, como chega no celular ou no rádio</p></div></div>",
        unsafe_allow_html=True)
    escolhido = st.selectbox("Seu município", nomes_por_focos, key="mun_agricultor")
    linha = atual[atual["nm_municipio"] == escolhido].iloc[0]
    canal = st.radio("Como o boletim chega", ["WhatsApp", "SMS", "Rádio"], horizontal=True,
                     index=0 if linha.canal_envio == "whatsapp" else 2)

    esq, dir_ = st.columns([1, 1])
    with esq:
        corpo = ""
        if canal == "WhatsApp":
            baloes = []
            if aviso:
                baloes.append("Período de alto risco de fogo no Pará.")
            baloes.append(f"{selo(linha.nivel_final)}<br>{motivo(linha)}")
            baloes.append(f"<b>O que fazer:</b> {linha.acao_final}")
            corpo = "".join(f"<div class='ac-balao'>{b}<span class='ac-hora'>seg 06:00</span></div>" for b in baloes)
            corpo += ("<div class='ac-balao'><div class='ac-audio'><div class='ac-play'>▶</div>"
                      "<div class='ac-onda'></div><small>0:24</small></div>"
                      "<span class='ac-hora'>Boletim em áudio · seg 06:00</span></div>")
            corpo += "<div class='ac-balao' style='font-size:.82rem;color:#5B6478'>Aviso automático, pode errar. Para sair: SAIR.</div>"
        elif canal == "SMS":
            corpo = (f"<div class='ac-sms'>{linha.sms_final}</div>"
                     f"<p style='color:#5B6478;font-size:.8rem;margin-top:6px'>{len(linha.sms_final)} de 160 caracteres, "
                     "sem acento, para caber em uma mensagem.</p>")
        else:
            corpo = (f"<div class='ac-balao'>🎙️ <b>Rádio comunitário</b><br>{texto_radio(linha)}</div>"
                     "<p style='color:#5B6478;font-size:.8rem'>Texto lido pelo locutor ou levado pelo técnico na visita.</p>")
        st.markdown(
            f"<div class='ac-celular'><div class='ac-cel-topo'>{SIMBOLO}<div>Aceiro<small>Boletim de "
            f"{linha.nm_municipio}</small></div></div><div class='ac-cel-corpo'>{corpo}</div></div>",
            unsafe_allow_html=True)
    with dir_:
        st.markdown(f"#### {linha.nm_municipio}: {selo(linha.nivel_final)}", unsafe_allow_html=True)
        st.markdown(f"**O que esse nível quer dizer:** {SIGNIFICADO[linha.nivel_final]}")
        if linha.ajustado:
            st.caption(f"O técnico ajustou o nível nesta sessão (o automático era {linha.nivel_alerta}).")
        st.markdown(f"**Canal principal:** {CANAL[linha.canal_envio]}. "
                    f"O 4G cobre {linha.pct_area_4g:.0f}% da área do município.")
        serie = bol[bol["nm_municipio"] == escolhido].set_index("semana_ref")["qtd_focos"].rename("Focos por semana")
        st.markdown("**Focos de calor no município, semana a semana**")
        st.bar_chart(serie, color=CORES["laranja"], height=220)
        st.caption("Foco de calor é o que o satélite detecta. Não confirma incêndio nem dano à roça.")
    rodape()


def pagina_tecnico():
    st.markdown(
        f"<div class='ac-topo'>{SIMBOLO}<div><div class='ac-h1'>Painel do técnico</div>"
        f"<p>Boletim da semana {semana}, de {inicio:%d/%m} a {(inicio + pd.to_timedelta(6, unit="D")):%d/%m} · 144 municípios do Pará</p></div></div>",
        unsafe_allow_html=True)
    if aviso:
        st.markdown("<div class='ac-aviso'><b>Aviso de período ativo.</b> El Niño forte e foco em mais da metade "
                    "dos municípios. Todos recebem a orientação de preparar o aceiro e evitar queimar.</div>",
                    unsafe_allow_html=True)

    filtro = st.multiselect("Níveis no mapa e na tabela", NIVEIS, default=NIVEIS)
    alerta = atual["nivel_final"].isin(["laranja", "vermelho"]).sum()
    revisados = {d["cod_municipio"] for d in st.session_state.decisoes if d["semana"] == semana}
    fila = atual[(atual["nivel_alerta"] == "vermelho") & (~atual["cod_municipio"].isin(revisados))]
    focos = int(atual["qtd_focos"].sum())
    delta = focos - int(anterior["qtd_focos"].sum()) if anterior is not None else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Em alerta", f"{alerta} de {len(atual)}", help="Municípios em laranja ou vermelho")
    c2.metric("Vermelhos na fila", f"{len(fila)}", help="Boletins vermelhos esperando a revisão do técnico")
    c3.metric("Focos na semana", f"{focos:,}".replace(",", "."),
              delta=None if delta is None else f"{delta:+,}".replace(",", "."), delta_color="inverse")
    c4.metric("Com foco", f"{atual['pct_mun_com_foco'].iloc[0]:.0f}%", help="Municípios com pelo menos um foco na semana")

    aba_mapa, aba_fila, aba_boletim, aba_tendencia = st.tabs(
        ["Mapa", f"Fila de revisão ({len(fila)})", "Boletim do município", "Tendência"])

    with aba_mapa:
        info = atual.set_index("cod_municipio")
        geo = copy.deepcopy(malha)
        feicoes = []
        for f in geo["features"]:
            cod = f["properties"]["codarea"]
            if cod not in info.index:
                continue
            linha = info.loc[cod]
            if linha["nivel_final"] not in filtro:
                continue
            f["properties"].update({
                "nome": linha["nm_municipio"],
                "nivel": linha["nivel_final"],
                "focos": int(linha["qtd_focos"]),
                "cor": rgb(CORES[linha["nivel_final"]]),
            })
            feicoes.append(f)
        geo["features"] = feicoes
        camada = pdk.Layer(
            "GeoJsonLayer", geo, pickable=True, stroked=True, filled=True,
            get_fill_color="properties.cor", get_line_color=[251, 249, 245, 200], line_width_min_pixels=0.6,
        )
        col_mapa, col_tabela = st.columns([5, 4])
        with col_mapa:
            st.pydeck_chart(pdk.Deck(
                layers=[camada],
                initial_view_state=pdk.ViewState(latitude=-4.0, longitude=-52.6, zoom=4.75),
                tooltip={"html": "<b>{nome}</b><br/>Nível: {nivel}<br/>Focos na semana: {focos}"},
                map_style=None,
            ), use_container_width=True, height=520)
            legenda = "".join(f"<div><span class='ac-pt' style='background:{CORES[n]}'></span>{n.capitalize()} "
                              f"<b>{int((atual['nivel_final'] == n).sum())}</b></div>" for n in NIVEIS)
            st.markdown(f"<div class='ac-legenda'>{legenda}</div>", unsafe_allow_html=True)
        tabela = (atual[atual["nivel_final"].isin(filtro)]
                  .sort_values("qtd_focos", ascending=False)
                  [["nm_municipio", "nivel_final", "qtd_focos", "dias_sem_chuva_mediana", "canal_envio", "pct_area_4g"]]
                  .rename(columns={"nm_municipio": "Município", "nivel_final": "Nível", "qtd_focos": "Focos",
                                   "dias_sem_chuva_mediana": "Dias sem chuva", "canal_envio": "Canal",
                                   "pct_area_4g": "4G (% área)"}))
        estilo = tabela.style.map(lambda n: f"color:{CORES[n]};font-weight:700", subset=["Nível"]).format(
            {"Dias sem chuva": "{:.0f}", "4G (% área)": "{:.0f}"}, na_rep="–")
        with col_tabela:
            st.dataframe(estilo, hide_index=True, use_container_width=True, height=560,
                         column_config={"Município": st.column_config.TextColumn(width="medium"),
                                        "Dias sem chuva": st.column_config.Column("Dias s/ chuva")})

    with aba_fila:
        st.caption("Vermelho só sai depois da revisão. Para baixar o nível, o motivo é obrigatório. "
                   "**Simulação:** as decisões ficam só nesta sessão e nada é enviado.")
        if fila.empty:
            st.success("Nenhum boletim vermelho esperando revisão nesta semana.")
        for _, linha in fila.sort_values("qtd_focos", ascending=False).iterrows():
            with st.expander(f"{linha.nm_municipio} · {linha.qtd_focos} focos na semana"):
                esq, direita = st.columns([3, 2])
                with esq:
                    st.markdown(texto_whatsapp(linha, aviso))
                    st.caption(f"Canal principal: {CANAL[linha.canal_envio]} · 4G em {linha.pct_area_4g:.0f}% da área")
                with direita:
                    novo = st.selectbox("Nível final", NIVEIS, index=3, key=f"nivel_{semana}_{linha.cod_municipio}")
                    justificativa = st.text_input("Motivo (obrigatório para baixar)",
                                                  key=f"motivo_{semana}_{linha.cod_municipio}")
                    if st.button("Registrar decisão", key=f"ok_{semana}_{linha.cod_municipio}", type="primary"):
                        if novo != "vermelho" and not justificativa.strip():
                            st.error("Para baixar um vermelho, escreva o motivo.")
                        else:
                            st.session_state.decisoes.append({
                                "semana": semana, "cod_municipio": linha.cod_municipio,
                                "municipio": linha.nm_municipio, "nivel_final": novo,
                                "motivo": justificativa.strip() or "aprovado sem mudança",
                                "registrado_em": datetime.now().strftime("%d/%m %H:%M"),
                            })
                            st.rerun()
        if st.session_state.decisoes:
            st.subheader("Decisões registradas nesta sessão")
            st.dataframe(pd.DataFrame(st.session_state.decisoes), hide_index=True, use_container_width=True)

    with aba_boletim:
        escolhido = st.selectbox("Município", nomes_por_focos)
        linha = atual[atual["nm_municipio"] == escolhido].iloc[0]
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**WhatsApp**")
            st.markdown(selo(linha.nivel_final), unsafe_allow_html=True)
            if linha.ajustado:
                st.caption(f"Nível ajustado pelo técnico (o automático era {linha.nivel_alerta}).")
            st.info(texto_whatsapp(linha, aviso))
        with col_b:
            st.markdown("**SMS** (sem acento, 1 mensagem)")
            st.code(linha.sms_final, language=None, wrap_lines=True)
            st.caption(f"{len(linha.sms_final)} de 160 caracteres")
        with col_c:
            st.markdown("**Rádio e visita**")
            st.success(texto_radio(linha))
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("População (2022)", f"{int(linha.qtd_populacao_2022):,}".replace(",", "."))
        m2.metric("Estab. da agricultura familiar", f"{int(linha.qtd_estab_agro_familiar):,}".replace(",", "."))
        m3.metric("Agricultura familiar", f"{linha.pct_agro_familiar:.0f}%")
        m4.metric("Área com 4G", f"{linha.pct_area_4g:.0f}%")
        st.caption(f"Canal principal: {CANAL[linha.canal_envio]}. Fontes: IBGE (Censo 2022 e Agro 2017) e Anatel.")

    with aba_tendencia:
        mun = st.selectbox("Comparar com o estado", nomes_por_focos, key="tendencia")
        serie_mun = bol[bol["nm_municipio"] == mun].set_index("semana_ref")["qtd_focos"].rename(mun)
        serie_pa = bol.groupby("semana_ref")["qtd_focos"].sum().rename("Pará (total)")
        st.markdown(f"**Focos por semana: {mun}**")
        st.bar_chart(serie_mun, color=CORES["laranja"])
        st.markdown("**Focos por semana: Pará**")
        st.line_chart(serie_pa, color="#1E2A4A")
        st.caption("As semanas 2026-W31 e 2026-W44 estão incompletas.")
    rodape()


def pagina_dados():
    st.markdown(
        f"<div class='ac-topo'>{SIMBOLO}<div><div class='ac-h1'>Sobre os dados</div>"
        "<p>De onde vem cada número e o que o Aceiro não promete</p></div></div>",
        unsafe_allow_html=True)
    st.markdown("""
**De onde vêm os dados**
- Focos de calor: INPE, BDQueimadas, só o satélite de referência (AQUA_M-T), de 01/08 a 31/10/2026.
- Municípios: IBGE (Censo 2022 e Censo Agropecuário 2017).
- Cobertura 4G: Anatel, painel Meu Município (set/2025).
- El Niño: índice RONI da NOAA, o valor já publicado no começo de cada mês.

**Regra de demonstração do nível**
- Verde: 0 focos · Amarelo: 1 a 4 · Laranja: 5 a 19 · Vermelho: 20 ou mais.
- Com El Niño forte (RONI ≥ 1,5), nenhum município fica verde.
- O aviso de período é aproximado pela % de municípios com foco, porque a grade de risco do INPE não entra aqui.
- O projeto também tem um modelo estatístico (regressão logística), testado à parte. Este protótipo não usa o modelo.

**Limites**
- Foco de calor não é incêndio confirmado nem dano às famílias.
- O alerta é por município: o Aceiro não sabe onde fica cada propriedade.
- O Aceiro não prevê onde o fogo começa. Por isso existe o aviso de período, para todos.
- As ações são um rascunho e precisam de revisão técnica da Emater.
- As personas e o uso do painel ainda não foram validados com agricultores e técnicos. Isso fica para a próxima etapa.
""")
    rodape()


PAGINAS = {
    "inicio": st.Page(pagina_inicio, title="Início", icon="🏠", default=True, url_path="inicio"),
    "agricultor": st.Page(pagina_agricultor, title="Visão do agricultor", icon="📱", url_path="agricultor"),
    "tecnico": st.Page(pagina_tecnico, title="Painel do técnico", icon="🗺️", url_path="tecnico"),
    "dados": st.Page(pagina_dados, title="Sobre os dados", icon="ℹ️", url_path="dados"),
}
st.navigation(list(PAGINAS.values())).run()
