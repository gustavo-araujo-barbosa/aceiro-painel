"""Prepara os dados do painel do técnico a partir dos dados reais do Aceiro.

Usa a mesma regra de demonstração de sql/03_gerar_boletins.sql, para o painel e o banco
mostrarem os mesmos boletins.

Entradas:
    data/processed/cad_municipio.csv
    data/processed/inpe_focos_ref_AAAAMM.csv
    data/raw/noaa_roni_202611.txt
    data/raw/ibge_malha_municipios_pa_2026.geojson

Uso (na raiz do repositório):
    python app/preparar_dados.py

Saídas (pequenas, cerca de 0,8 MB no total):
    app/dados/boletins_semana.csv   1 linha por município por semana, com focos, nível e textos
    app/dados/municipios.geojson    malha dos municípios do Pará (IBGE)
"""

import json
import re
import shutil
from pathlib import Path

import pandas as pd

from regras import TRIMESTRE_VIGENTE, acao, nivel, texto_sms

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
BRUTO = RAIZ / "data" / "raw"
SAIDA = RAIZ / "app" / "dados"




def ler_roni():
    valores = {}
    for linha in (BRUTO / "noaa_roni_202611.txt").read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if len(partes) == 3 and partes[1] == "2026":
            valores[partes[0]] = float(partes[2])
    return {mes: valores.get(tri) for mes, tri in TRIMESTRE_VIGENTE.items()}



def main():
    cad = pd.read_csv(PROC / "cad_municipio.csv", dtype={"cod_municipio": str})
    # Só os arquivos mensais no padrão exato (evita somar cópias e backups)
    arquivos = sorted(f for f in PROC.glob("inpe_focos_ref_*.csv") if re.fullmatch(r"inpe_focos_ref_\d{6}\.csv", f.name))
    focos = pd.concat([pd.read_csv(f, dtype={"municipio_id": str}) for f in arquivos], ignore_index=True)
    repetidos = focos["id"].duplicated().sum()
    if repetidos:
        print(f"Aviso: {repetidos} focos repetidos foram descartados")
        focos = focos.drop_duplicates("id")
    focos = focos[focos["satelite"] == "AQUA_M-T"].copy()
    for col in ("risco_fogo", "numero_dias_sem_chuva", "precipitacao"):
        focos[col] = pd.to_numeric(focos[col], errors="coerce").where(lambda s: s != -999)

    # Horário de Belém (UTC-3) e semana ISO, como as colunas virtuais do banco
    local = pd.to_datetime(focos["data_hora_gmt"]) - pd.to_timedelta(3, unit="h")
    iso = local.dt.isocalendar()
    focos["semana_ref"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    focos["inicio_semana"] = (local - pd.to_timedelta(local.dt.weekday, unit="D")).dt.normalize()
    focos["cod_municipio"] = focos["municipio_id"]

    semanas = focos.groupby("semana_ref", as_index=False)["inicio_semana"].min()
    por_semana = focos.groupby(["cod_municipio", "semana_ref"]).agg(
        qtd_focos=("id", "size"),
        risco_medio=("risco_fogo", "mean"),
        sem_risco=("risco_fogo", lambda s: s.isna().sum()),
        dias_sem_chuva_mediana=("numero_dias_sem_chuva", "median"),
        frp_max=("frp", "max"),
    ).reset_index()

    grade = cad.merge(semanas, how="cross").merge(por_semana, how="left", on=["cod_municipio", "semana_ref"])
    grade["qtd_focos"] = grade["qtd_focos"].fillna(0).astype(int)
    grade["pct_focos_sem_dado"] = (100 * grade["sem_risco"] / grade["qtd_focos"].where(grade["qtd_focos"] > 0)).round(2)
    grade["risco_medio"] = grade["risco_medio"].round(2)

    roni = ler_roni()
    grade["roni_vigente"] = grade["inicio_semana"].dt.strftime("%Y-%m").map(roni)
    grade["nivel_alerta"] = [nivel(q, r) for q, r in zip(grade["qtd_focos"], grade["roni_vigente"])]

    pct_com_foco = grade.groupby("semana_ref")["qtd_focos"].apply(lambda s: 100 * (s > 0).mean())
    grade["pct_mun_com_foco"] = grade["semana_ref"].map(pct_com_foco).round(1)
    grade["fl_aviso_periodo"] = ((grade["pct_mun_com_foco"] >= 50) & (grade["roni_vigente"] >= 1.5)).map({True: "S", False: "N"})
    grade["canal_envio"] = grade["pct_area_4g"].lt(50).map({True: "radio", False: "whatsapp"})

    grade["acao_recomendada"] = grade["nivel_alerta"].map(acao)
    grade["texto_sms"] = [texto_sms(n, q) for n, q in zip(grade["nivel_alerta"], grade["qtd_focos"])]
    assert grade["texto_sms"].str.len().max() <= 160
    assert grade["texto_sms"].map(str.isascii).all()

    SAIDA.mkdir(parents=True, exist_ok=True)
    colunas = [
        "cod_municipio", "nm_municipio", "semana_ref", "inicio_semana", "qtd_focos", "risco_medio",
        "pct_focos_sem_dado", "dias_sem_chuva_mediana", "frp_max", "roni_vigente", "pct_mun_com_foco",
        "fl_aviso_periodo", "nivel_alerta", "acao_recomendada", "texto_sms", "canal_envio",
        "qtd_populacao_2022", "qtd_estab_agro_familiar", "pct_agro_familiar", "pct_area_4g", "pct_moradores_4g",
    ]
    grade[colunas].sort_values(["semana_ref", "nm_municipio"]).to_csv(SAIDA / "boletins_semana.csv", index=False)

    shutil.copy(BRUTO / "ibge_malha_municipios_pa_2026.geojson", SAIDA / "municipios.geojson")
    malha = json.loads((SAIDA / "municipios.geojson").read_text(encoding="utf-8"))
    print(f"{grade['cod_municipio'].nunique()} municípios x {grade['semana_ref'].nunique()} semanas "
          f"= {len(grade)} boletins; {len(malha['features'])} polígonos na malha; "
          f"{int(grade['qtd_focos'].sum())} focos")


if __name__ == "__main__":
    main()
