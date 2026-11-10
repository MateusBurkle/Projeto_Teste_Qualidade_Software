"""Cenario carga: CT-P12 - 100 usuarios simultaneos (RD-01, RC-04). Duracao NAO definida no Plano: 5 min (hipotese).

Uso: locust -f locustfile.py,cenario_carga.py PixUser --headless
"""
from locust import LoadTestShape

import comum

comum.definir_cenario("carga")
U = comum.USUARIOS_BASE
# (duracao_s, usuarios, taxa_de_entrada_por_s, fase)
ETAPAS = [(300, U, 10, "unica")]


class Forma(LoadTestShape):
    def tick(self):
        return comum.etapa_em(ETAPAS, self.get_run_time())
