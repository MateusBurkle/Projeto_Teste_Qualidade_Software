"""Apoio comum aos scripts Locust do NextBank (meta M5).

Carrega os modulos pix.py e extrato.py da fase REFACTOR (sao arquivos autonomos; os dois pacotes
se chamam 'nextbank', por isso sao carregados pelo caminho do arquivo) e guarda os parametros e o
estado compartilhado entre os usuarios virtuais e os cenarios.
"""
import importlib.util
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # Parte4_TDD

# pix.py faz "from nextbank.login import mascarar"; o login.py e identico em todos os modulos,
# entao basta a pasta do pix/refactor estar no caminho de imports.
sys.path.insert(0, str(RAIZ / "pix" / "refactor"))


def carregar_modulo(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


pix = carregar_modulo("nb_pix", RAIZ / "pix" / "refactor" / "nextbank" / "pix.py")
extrato = carregar_modulo("nb_extrato", RAIZ / "extrato" / "refactor" / "nextbank" / "extrato.py")

# ---- Parametros (variaveis de ambiente) ----------------------------------------------------
USUARIOS_BASE = int(os.getenv("NB_USUARIOS_BASE", "100"))  # Plano: 100 usuarios (carga normal)
ESCALA_TEMPO = float(os.getenv("NB_ESCALA_TEMPO", "1"))  # 1 = duracoes completas; 0.05 = teste rapido
PENSAR_MIN = float(os.getenv("NB_PENSAR_MIN", "1"))  # espera entre acoes (s); HIPOTESE, fora do Plano
PENSAR_MAX = float(os.getenv("NB_PENSAR_MAX", "3"))
PISO_MS = float(os.getenv("NB_PISO_MS", "1"))  # abaixo disto a variacao do tempo medio e ruido; HIPOTESE
N_LANCAMENTOS = int(os.getenv("NB_LANCAMENTOS", "50"))  # lancamentos por conta no extrato; HIPOTESE
LIMITE_E09 = int(os.getenv("NB_E09_REQUISICOES", "1000"))  # CT-E09: 1.000 requisicoes

# Limites do Plano (Quadro 10)
MEDIA_MAX_MS = 2000  # RD-01
P95_MAX_MS = 3000  # RD-01
ERRO_PICO_MAX = 0.01  # RD-02 (< 1%)
SUCESSO_MIN = 0.999  # RC-01 / carga normal (>= 99,9%)
CRESCIMENTO_MAX = 0.20  # RD-04 (<= +20%)
RECUPERACAO_S = 120  # RD-03 (2 min)

# ---- Estado compartilhado ---------------------------------------------------------------
estado = {"cenario": None, "fase": "unica"}


def definir_cenario(nome):
    estado["cenario"] = nome


def duracao(segundos):
    return segundos * ESCALA_TEMPO


def etapa_em(etapas, t):
    """etapas: lista de (duracao_s, usuarios, taxa_de_entrada, fase).

    Devolve (usuarios, taxa) da etapa em que o instante t (s) cai, ou None ao fim do cenario.
    """
    limite = 0
    for dur, usuarios, taxa, fase in etapas:
        limite += duracao(dur)
        if t < limite:
            estado["fase"] = fase
            return usuarios, taxa
    return None
