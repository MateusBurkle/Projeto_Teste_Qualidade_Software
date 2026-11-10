"""Cenario estresse: CT-P15 - degraus ate 20x a carga normal e recuperacao em 2 min (RD-03). Degraus e duracoes: hipoteses.

Uso: locust -f locustfile.py,cenario_estresse.py PixUser --headless
"""
from locust import LoadTestShape

import comum

comum.definir_cenario("estresse")
U = comum.USUARIOS_BASE
# (duracao_s, usuarios, taxa_de_entrada_por_s, fase)
ETAPAS = [
    (30, U, 10, "normal"),
    (60, 5 * U, 1000, "degrau-05x"),
    (60, 10 * U, 1000, "degrau-10x"),
    (60, 15 * U, 1000, "degrau-15x"),
    (60, 20 * U, 1000, "degrau-20x"),
    (comum.RECUPERACAO_S, U, 1000, "recuperacao"),
]


class Forma(LoadTestShape):
    def tick(self):
        return comum.etapa_em(ETAPAS, self.get_run_time())
