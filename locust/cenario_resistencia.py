"""Cenario resistencia: CT-P16 - carga normal por 30 min (RD-04, RC-04). Janelas inicio/fim = 10% cada (hipotese).

Uso: locust -f locustfile.py,cenario_resistencia.py PixUser --headless
"""
from locust import LoadTestShape

import comum

comum.definir_cenario("resistencia")
U = comum.USUARIOS_BASE
# (duracao_s, usuarios, taxa_de_entrada_por_s, fase)
ETAPAS = [(180, U, 10, "inicio"), (1440, U, 10, "meio"), (180, U, 10, "fim")]


class Forma(LoadTestShape):
    def tick(self):
        return comum.etapa_em(ETAPAS, self.get_run_time())
