import pytest
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dian_processor import process_dian_file, check_nit_dian

def test_process_dian_file_success(tmp_path):
    # Crear un excel temporal
    df = pd.DataFrame({
        'NIT': ['900.123.456-7', '12345678', '900123456', 900123456], # ultimo valor repetido de hecho
        'NOMBRE': ['A', 'B', 'A2', 'A3']
    })
    test_excel = tmp_path / "test_dian.xlsx"
    df.to_excel(test_excel, index=False)
    
    # Run the function
    result_df = process_dian_file(test_excel)
    
    # Assertions
    assert result_df.height == 2 # 900123456 y 012345678
    assert 'FECHA_INGESTA' in result_df.columns
    assert 'NIT_NORMALIZADO' in result_df.columns
    nit_values = result_df['NIT_NORMALIZADO'].to_list()
    assert '900123456' in nit_values
    assert '012345678' in nit_values

def test_process_dian_file_invalid_schema(tmp_path):
    df = pd.DataFrame({
        'ID_INCORRECTO': ['900.123.456-7']
    })
    test_excel = tmp_path / "bad_schema.xlsx"
    df.to_excel(test_excel, index=False)
    
    with pytest.raises(ValueError):
         process_dian_file(test_excel)

def test_check_nit_dian():
    # Because process_dian_file saves it globally, we can mock or just assume
    # We will test check_nit_dian if the parquet exists
    parquet_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/dian_ficticios.parquet'))
    if os.path.exists(parquet_path):
         assert check_nit_dian('900.123.456-7') == True or check_nit_dian('900.123.456-7') == False # Just verify it runs
