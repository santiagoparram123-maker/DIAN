import pytest
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from report_engine import calculate_risk

def test_calculate_risk_alto():
    riesgo, _ = calculate_risk(en_ficticios=True, estado_bdme="SIN_DEUDA", facturador_habilitado=True)
    assert riesgo == "ALTO"

def test_calculate_risk_medio_bdme():
    riesgo, _ = calculate_risk(en_ficticios=False, estado_bdme="EN_MORA", facturador_habilitado=True)
    assert riesgo == "MEDIO"

def test_calculate_risk_medio_facturador():
    riesgo, _ = calculate_risk(en_ficticios=False, estado_bdme="SIN_DEUDA", facturador_habilitado=False)
    assert riesgo == "MEDIO"

def test_calculate_risk_revisar():
    riesgo, _ = calculate_risk(en_ficticios=False, estado_bdme="INDETERMINADO", facturador_habilitado=True)
    assert riesgo == "REVISAR"

def test_calculate_risk_bajo():
    riesgo, _ = calculate_risk(en_ficticios=False, estado_bdme="SIN_DEUDA", facturador_habilitado=True)
    assert riesgo == "BAJO"

def test_calculate_risk_precedencia():
    # ALTO wins over MEDIO
    riesgo, _ = calculate_risk(en_ficticios=True, estado_bdme="EN_MORA", facturador_habilitado=False)
    assert riesgo == "ALTO"
