"""Regras de demonstração do boletim, usadas pelo preparo dos dados e pelo painel.

São as mesmas de sql/03_gerar_boletins.sql. Ficam num lugar só para o nível, a ação
e os textos dos canais nunca saírem diferentes entre si.
"""

NIVEIS = ["verde", "amarelo", "laranja", "vermelho"]

# Para cada mês, o RONI mais recente já publicado no começo do mês:
# o trimestre que termina no mês anterior (NOAA CPC, RONI.ascii.txt).
TRIMESTRE_VIGENTE = {
    "2026-07": "AMJ",
    "2026-08": "MJJ",
    "2026-09": "JJA",
    "2026-10": "JAS",
    "2026-11": "ASO",
}

# Rascunho de ações por nível: (texto do WhatsApp e do rádio, texto curto do SMS, sem acento).
# Precisa de revisão técnica da Emater antes do uso real.
ACOES = {
    "verde": ("Sem alerta no município nesta semana. Mantenha o aceiro limpo.",
              "Mantenha o aceiro limpo."),
    "amarelo": ("Fique atento: evite queimar e confira o aceiro em volta da roça e da casa.",
                "Evite queimar e confira o aceiro."),
    "laranja": ("Abra ou limpe o aceiro em volta da roça e da casa.",
                "Abra ou limpe o aceiro."),
    "vermelho": ("Não use fogo. Abra ou limpe o aceiro e fale com a Emater.",
                 "Nao use fogo. Abra o aceiro."),
}


def nivel(qtd_focos, roni):
    """Nível pela quantidade de focos na semana, com piso de alerta no El Niño forte."""
    if qtd_focos >= 20:
        return "vermelho"
    if qtd_focos >= 5:
        return "laranja"
    if qtd_focos >= 1:
        return "amarelo"
    if roni is not None and roni == roni and roni >= 1.5:  # roni == roni descarta NaN
        return "amarelo"
    return "verde"


def acao(nivel_alerta):
    return ACOES[nivel_alerta][0]


def texto_sms(nivel_alerta, qtd_focos):
    """SMS de uma mensagem só: até 160 caracteres e sem acento."""
    texto = (f"ACEIRO: nivel {nivel_alerta.upper()} no seu municipio. {int(qtd_focos)} focos de calor "
             f"na semana. {ACOES[nivel_alerta][1]} Pode errar. Duvida: Emater. Para sair: SAIR")
    assert len(texto) <= 160 and texto.isascii(), texto
    return texto
