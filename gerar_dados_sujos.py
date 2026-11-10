"""Gera uma planilha FICTÍCIA e propositalmente "suja" de inventário de ativos de TI.

Simula problemas comuns de planilhas preenchidas à mão: duplicatas, datas em vários
formatos, categorias escritas de jeitos diferentes, valores monetários como texto,
espaços extras, campos vazios e e-mails inválidos. Nenhum dado é real.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(2026)
N = 600

tipos = {
    "Notebook": ["Notebook", "notebook", "NOTEBOOK", "Notebok", " Notebook ", "Note book"],
    "Desktop": ["Desktop", "desktop", "Desk top", "DESKTOP"],
    "Monitor": ["Monitor", "monitor", "Monitor ", "MONITOR"],
    "Smartphone": ["Smartphone", "smartphone", "Celular", "Smart phone"],
    "Tablet": ["Tablet", "tablet", "TABLET", "Tablete"],
}
marcas = {
    "Notebook": ["Dell", "HP", "Lenovo"], "Desktop": ["Dell", "HP"],
    "Monitor": ["Dell", "LG", "Samsung"], "Smartphone": ["Apple", "Samsung", "Motorola"],
    "Tablet": ["Apple", "Samsung"],
}
precos = {"Notebook": 6500, "Desktop": 4800, "Monitor": 1300, "Smartphone": 4200, "Tablet": 3500}
status_var = {"Em uso": ["Em uso", "em uso", "EM USO", "Em Uso", "uso"],
              "Estoque": ["Estoque", "estoque", "Em estoque"],
              "Manutenção": ["Manutenção", "manutencao", "Manutencao", "Em manutenção"],
              "Descartado": ["Descartado", "descartado", "Baixado"]}
deptos = ["Financeiro", "RH", "TI", "Engenharia", "Comercial", "Diretoria", "Logística"]
nomes = ["Ana", "Bruno", "Carla", "Diego", "Elaine", "Fábio", "Gabriela", "Hugo",
         "Isabela", "João", "Karen", "Lucas", "Mariana", "Nelson", "Olívia", "Pedro"]
sobrenomes = ["Silva", "Souza", "Oliveira", "Santos", "Lima", "Costa", "Pereira", "Almeida"]

def data_suja(d):
    fmt = rng.choice(["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y"],
                     p=[.5, .2, .1, .1, .1])
    return d.strftime(fmt)

def valor_sujo(v):
    estilo = rng.integers(0, 4)
    if estilo == 0:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if estilo == 1:
        return f"{v:.2f}".replace(".", ",")
    if estilo == 2:
        return f"{v:.2f}"
    return f"R${v:,.0f}".replace(",", ".")

linhas = []
for i in range(N):
    tipo = rng.choice(list(tipos), p=[.35, .15, .25, .15, .10])
    nome, sob = rng.choice(nomes), rng.choice(sobrenomes)
    compra = pd.Timestamp("2021-01-01") + pd.Timedelta(days=int(rng.integers(0, 1800)))
    status = rng.choice(list(status_var), p=[.70, .12, .10, .08])
    serial = f"{rng.choice(list('ABCDEFGH'))}{rng.integers(100000, 999999)}"
    linhas.append({
        "Patrimonio": f"PAT-{10000 + i}",
        "Num Serie": serial if rng.random() > .1 else f" {serial.lower()} ",
        "Tipo Equipamento": rng.choice(tipos[tipo]),
        "Marca": rng.choice(marcas[tipo]) if rng.random() > .05 else rng.choice(marcas[tipo]).lower(),
        "Usuario": f"{nome} {sob}" if rng.random() > .1 else f"  {nome.upper()} {sob} ",
        "Email": (f"{nome.lower()}.{sob.lower()}@empresa-ficticia.com.br" if rng.random() > .06
                  else rng.choice([f"{nome.lower()}{sob.lower()}empresa.com", "", "n/a"])),
        "Departamento": rng.choice(deptos) if rng.random() > .07 else rng.choice(["", "-", "rh", "ti"]),
        "Data Compra": data_suja(compra),
        "Valor Compra": valor_sujo(precos[tipo] * rng.uniform(.8, 1.2)),
        "Status": rng.choice(status_var[status]),
    })

df = pd.DataFrame(linhas)
# problemas extras
df.loc[rng.choice(N, 12, replace=False), "Data Compra"] = rng.choice(["", "sem data", "31/02/2023", "15/13/2022"], 12)
df.loc[rng.choice(N, 5, replace=False), "Data Compra"] = "10/05/2031"  # data no futuro
df.loc[rng.choice(N, 8, replace=False), "Valor Compra"] = rng.choice(["", "-", "verificar"], 8)
df.loc[rng.choice(N, 4, replace=False), "Valor Compra"] = "-500,00"  # valor negativo
dups = df.sample(25, random_state=1)                              # duplicatas exatas
dups2 = df.sample(10, random_state=2).assign(Usuario=lambda x: x["Usuario"].str.upper())  # duplicatas "disfarçadas"
df = pd.concat([df, dups, dups2]).sample(frac=1, random_state=3).reset_index(drop=True)

df.to_csv("dados/brutos/inventario_ativos_bruto.csv", sep=";", index=False, encoding="utf-8-sig")
print(f"{len(df)} linhas geradas em dados/brutos/inventario_ativos_bruto.csv")
