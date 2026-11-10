"""ETL de inventário de ativos de TI com pandas.

Extract   -> lê o CSV bruto exportado do Excel (separador ';')
Transform -> padroniza texto, categorias, datas e valores; remove duplicatas
Validate  -> marca registros com problemas em vez de apagá-los
Load      -> grava CSV limpo, CSV de rejeitados, banco SQLite e relatório de qualidade
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
ENTRADA = BASE / "dados" / "brutos" / "inventario_ativos_bruto.csv"
SAIDA = BASE / "saida"

MAPA_TIPO = {
    "notebook": "Notebook", "notebok": "Notebook", "note book": "Notebook",
    "desktop": "Desktop", "desk top": "Desktop",
    "monitor": "Monitor",
    "smartphone": "Smartphone", "smart phone": "Smartphone", "celular": "Smartphone",
    "tablet": "Tablet", "tablete": "Tablet",
}
MAPA_STATUS = {
    "em uso": "Em uso", "uso": "Em uso",
    "estoque": "Estoque", "em estoque": "Estoque",
    "manutencao": "Manutenção", "em manutencao": "Manutenção",
    "descartado": "Descartado", "baixado": "Descartado",
}
MAPA_DEPTO = {"rh": "RH", "ti": "TI"}
SIGLAS_MARCA = {"hp": "HP", "lg": "LG"}
VAZIOS = {"", "-", "n/a", "na", "sem data", "verificar", "nan"}
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
FORMATOS_DATA = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y"]


# ---------- funções de limpeza (testáveis isoladamente) ----------

def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def chave(texto) -> str:
    """Normaliza texto para comparação: minúsculo, sem acento, espaços colapsados."""
    if pd.isna(texto):
        return ""
    return re.sub(r"\s+", " ", sem_acento(str(texto)).strip().lower())


def limpar_nome(texto) -> str | None:
    """Colapsa espaços e aplica Iniciais Maiúsculas, preservando acentos."""
    if chave(texto) in VAZIOS:
        return None
    return " ".join(p.capitalize() for p in str(texto).split())


def limpar_marca(texto) -> str | None:
    nome = limpar_nome(texto)
    return SIGLAS_MARCA.get(nome.lower(), nome) if nome else None


def converter_data(texto) -> pd.Timestamp | None:
    k = chave(texto)
    if k in VAZIOS:
        return None
    for fmt in FORMATOS_DATA:
        try:
            return pd.to_datetime(k, format=fmt)
        except ValueError:
            continue
    return None  # datas impossíveis (31/02, mês 13) caem aqui


def converter_valor(texto) -> float | None:
    k = chave(texto).replace("r$", "").replace(" ", "")
    if k in VAZIOS:
        return None
    if "," in k:                       # formato brasileiro: 1.234,56
        k = k.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", k):  # 5.433 -> milhar
        k = k.replace(".", "")
    try:
        return float(k)
    except ValueError:
        return None


# ---------- etapas ----------

def extrair(caminho: Path = ENTRADA) -> pd.DataFrame:
    return pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def transformar(bruto: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame({
        "patrimonio": bruto["Patrimonio"].str.strip().str.upper(),
        "num_serie": bruto["Num Serie"].str.strip().str.upper(),
        "tipo": bruto["Tipo Equipamento"].map(chave).map(MAPA_TIPO),
        "marca": bruto["Marca"].map(limpar_marca),
        "usuario": bruto["Usuario"].map(limpar_nome),
        "email": bruto["Email"].map(chave).replace(list(VAZIOS), None),
        "departamento": bruto["Departamento"].map(
            lambda x: MAPA_DEPTO.get(chave(x), None if chave(x) in VAZIOS else str(x).strip())),
        "data_compra": bruto["Data Compra"].map(converter_data),
        "valor_compra": bruto["Valor Compra"].map(converter_valor),
        "status": bruto["Status"].map(chave).map(MAPA_STATUS),
    })
    df["data_compra"] = pd.to_datetime(df["data_compra"])
    # duplicatas exatas e "disfarçadas" (mesmo patrimônio e série após padronização)
    df = df.drop_duplicates(subset=["patrimonio", "num_serie"], keep="first").reset_index(drop=True)
    return df


def validar(df: pd.DataFrame, hoje: date | None = None) -> pd.DataFrame:
    hoje = pd.Timestamp(hoje or date.today())
    problemas = pd.DataFrame(index=df.index)
    problemas["tipo_desconhecido"] = df["tipo"].isna()
    problemas["status_desconhecido"] = df["status"].isna()
    problemas["data_invalida"] = df["data_compra"].isna()
    problemas["data_futura"] = df["data_compra"] > hoje
    problemas["valor_ausente"] = df["valor_compra"].isna()
    problemas["valor_negativo"] = df["valor_compra"] < 0
    problemas["email_invalido"] = ~df["email"].fillna("").str.match(EMAIL_RE)
    problemas["departamento_ausente"] = df["departamento"].isna()

    df = df.copy()
    df["problemas"] = problemas.apply(lambda r: ", ".join(c for c in problemas.columns if r[c]), axis=1)
    # críticos impedem o uso analítico; os demais ficam como alerta
    criticos = ["tipo_desconhecido", "data_invalida", "data_futura", "valor_ausente", "valor_negativo"]
    df["registro_valido"] = ~problemas[criticos].any(axis=1)
    return df


def carregar(df: pd.DataFrame, bruto_linhas: int, destino: Path = SAIDA) -> dict:
    destino.mkdir(exist_ok=True)
    validos = df[df["registro_valido"]].drop(columns=["registro_valido"])
    rejeitados = df[~df["registro_valido"]].drop(columns=["registro_valido"])
    validos.to_csv(destino / "inventario_limpo.csv", index=False, date_format="%Y-%m-%d")
    rejeitados.to_csv(destino / "inventario_rejeitados.csv", index=False, date_format="%Y-%m-%d")
    with sqlite3.connect(destino / "inventario.db") as con:
        validos.to_sql("ativos", con, if_exists="replace", index=False)

    contagem = (df["problemas"].str.split(", ").explode().loc[lambda s: s != ""].value_counts())
    resumo = {
        "linhas_brutas": bruto_linhas,
        "duplicatas_removidas": bruto_linhas - len(df),
        "registros_validos": len(validos),
        "registros_rejeitados": len(rejeitados),
        "problemas": contagem.to_dict(),
    }
    escrever_relatorio(resumo, validos, destino / "relatorio_qualidade.md")
    return resumo


def escrever_relatorio(resumo: dict, validos: pd.DataFrame, caminho: Path) -> None:
    linhas = [
        "# Relatório de qualidade dos dados",
        "",
        "| Métrica | Valor |", "|---|---|",
        f"| Linhas na planilha bruta | {resumo['linhas_brutas']} |",
        f"| Duplicatas removidas | {resumo['duplicatas_removidas']} |",
        f"| Registros válidos | {resumo['registros_validos']} |",
        f"| Registros rejeitados (problema crítico) | {resumo['registros_rejeitados']} |",
        "", "## Problemas encontrados", "",
        "| Problema | Ocorrências |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in resumo["problemas"].items()],
        "", "## Valor do parque por tipo (registros válidos)", "",
        "| Tipo | Quantidade | Valor total (R$) |", "|---|---|---|",
    ]
    por_tipo = validos.groupby("tipo")["valor_compra"].agg(["count", "sum"]).sort_values("sum", ascending=False)
    for tipo, r in por_tipo.iterrows():
        valor = f"{r['sum']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas.append(f"| {tipo} | {int(r['count'])} | {valor} |")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> None:
    bruto = extrair()
    df = validar(transformar(bruto))
    resumo = carregar(df, len(bruto))
    print(f"Linhas brutas: {resumo['linhas_brutas']} | duplicatas removidas: {resumo['duplicatas_removidas']}")
    print(f"Válidos: {resumo['registros_validos']} | rejeitados: {resumo['registros_rejeitados']}")
    print("Saídas em ./saida (CSV limpo, rejeitados, SQLite e relatório)")


if __name__ == "__main__":
    main()
