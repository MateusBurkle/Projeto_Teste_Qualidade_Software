"""Cenario pico: CT-P13 - salto para 10x a carga normal e recuperacao (RD-02). Duracoes: hipoteses.

Uso: locust -f locustfile.py,cenario_pico.py PixUser --headless
"""
from locust import LoadTestShape

import comum

comum.definir_cenario("pico")
U = comum.USUARIOS_BASE
# (duracao_s, usuarios, taxa_de_entrada_por_s, fase)
ETAPAS = [(30, U, 10, "normal"), (60, 10 * U, 1000, "pico"), (comum.RECUPERACAO_S, U, 1000, "recuperacao")]


class Forma(LoadTestShape):
    def tick(self):
        return comum.etapa_em(ETAPAS, self.get_run_time())
