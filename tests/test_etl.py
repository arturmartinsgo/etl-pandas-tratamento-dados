import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import etl  # noqa: E402


def test_converter_valor_formatos():
    assert etl.converter_valor("R$ 1.234,56") == 1234.56
    assert etl.converter_valor("1480,20") == 1480.20
    assert etl.converter_valor("4175.90") == 4175.90
    assert etl.converter_valor("R$5.433") == 5433
    assert etl.converter_valor("verificar") is None
    assert etl.converter_valor("") is None


def test_converter_data_formatos_e_invalidas():
    alvo = pd.Timestamp("2024-03-04")
    for texto in ["04/03/2024", "2024-03-04", "04-03-2024", "04/03/24", "04.03.2024"]:
        assert etl.converter_data(texto) == alvo
    assert etl.converter_data("31/02/2023") is None
    assert etl.converter_data("15/13/2022") is None
    assert etl.converter_data("sem data") is None


def test_limpar_nome_preserva_acento():
    assert etl.limpar_nome("  FÁBIO   souza ") == "Fábio Souza"
    assert etl.limpar_marca("hp") == "HP"


def test_pipeline_remove_duplicatas_e_marca_problemas():
    bruto = pd.DataFrame({
        "Patrimonio": ["PAT-1", "PAT-1", "PAT-2"],
        "Num Serie": ["A1", " a1 ", "B2"],
        "Tipo Equipamento": ["Notebok", "notebook", "Desk top"],
        "Marca": ["Dell", "dell", "hp"],
        "Usuario": ["Ana Silva", "ANA SILVA", "Bruno Lima"],
        "Email": ["ana.silva@x.com", "ana.silva@x.com", "n/a"],
        "Departamento": ["TI", "TI", "rh"],
        "Data Compra": ["01/02/2024", "01/02/2024", "10/05/2031"],
        "Valor Compra": ["R$ 6.000,00", "6000,00", "-500,00"],
        "Status": ["em uso", "EM USO", "Baixado"],
    })
    df = etl.validar(etl.transformar(bruto), hoje=date(2026, 11, 10))
    assert len(df) == 2
    assert df.loc[0, "tipo"] == "Notebook" and df.loc[0, "registro_valido"]
    assert not df.loc[1, "registro_valido"]
    assert {"data_futura", "valor_negativo", "email_invalido"} <= set(df.loc[1, "problemas"].split(", "))
