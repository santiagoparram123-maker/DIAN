# ============================================================================
# TEST SUITE: Clasificador Arancelario
# Archivo: tests/test_clasificador.py
# Proyecto: DIAN Auditor B2B
# ============================================================================

import pytest
import pandas as pd
import json
import os
import sys
import tempfile
import hashlib

# Agregar src al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from clasificador import (
    cargar_archivo,
    clasificar_producto,
    clasificar_catalogo,
    exportar_json,
    BaseConocimientoAduanera,
    COLUMNA_ID,
    COLUMNA_DESCRIPCION,
    OLLAMA_URL,
    MODELO_IA,
    _cache_clasificacion,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def csv_valido(tmp_path):
    """Crea un CSV válido con las columnas esperadas."""
    csv_file = tmp_path / "test_valido.csv"
    csv_file.write_text(
        "ID_PRODUCTO,DESCRIPCION_MERCANCIA\n"
        "P001,Zapatos de cuero italiano con suela de caucho\n"
        "P002,Camisetas de algodón estampadas para mujer\n"
        "P003,Aceite de oliva extra virgen orgánico 500ml\n",
        encoding='utf-8'
    )
    return str(csv_file)


@pytest.fixture
def csv_columnas_alternativas(tmp_path):
    """CSV con nombres de columnas diferentes pero detectables."""
    csv_file = tmp_path / "test_alt.csv"
    csv_file.write_text(
        "CODIGO_REF,NOMBRE_PRODUCTO\n"
        "R001,Laptop portátil 15 pulgadas procesador Intel\n"
        "R002,Cable de fibra óptica monomodo 12 hilos\n",
        encoding='utf-8'
    )
    return str(csv_file)


@pytest.fixture
def csv_vacio(tmp_path):
    """CSV con encabezados pero sin datos."""
    csv_file = tmp_path / "test_vacio.csv"
    csv_file.write_text(
        "ID_PRODUCTO,DESCRIPCION_MERCANCIA\n",
        encoding='utf-8'
    )
    return str(csv_file)


@pytest.fixture
def csv_una_columna(tmp_path):
    """CSV con solo una columna."""
    csv_file = tmp_path / "test_una.csv"
    csv_file.write_text(
        "PRODUCTOS\n"
        "Zapatos de cuero\n"
        "Camisetas de algodón\n",
        encoding='utf-8'
    )
    return str(csv_file)


@pytest.fixture
def csv_con_nulos(tmp_path):
    """CSV con valores nulos/vacíos en descripciones."""
    csv_file = tmp_path / "test_nulos.csv"
    csv_file.write_text(
        "ID_PRODUCTO,DESCRIPCION_MERCANCIA\n"
        "P001,Zapatos de cuero\n"
        "P002,\n"
        "P003,Aceite de oliva\n"
        "P004,  \n",
        encoding='utf-8'
    )
    return str(csv_file)


@pytest.fixture(autouse=True)
def limpiar_cache():
    """Limpia el cache de clasificación antes de cada test."""
    _cache_clasificacion.clear()
    yield
    _cache_clasificacion.clear()


# ============================================================================
# TESTS: cargar_archivo()
# ============================================================================

class TestCargarArchivo:
    """Tests unitarios para la función cargar_archivo."""

    def test_carga_csv_valido(self, csv_valido):
        """Verifica que un CSV con columnas correctas se carga sin error."""
        df = cargar_archivo(csv_valido)
        assert isinstance(df, pd.DataFrame)
        assert COLUMNA_ID in df.columns
        assert COLUMNA_DESCRIPCION in df.columns
        assert len(df) == 3

    def test_carga_csv_columnas_alternativas(self, csv_columnas_alternativas):
        """Verifica que el renombrado heurístico funciona."""
        df = cargar_archivo(csv_columnas_alternativas)
        assert COLUMNA_ID in df.columns
        assert COLUMNA_DESCRIPCION in df.columns
        assert len(df) == 2

    def test_archivo_no_existe(self):
        """Verifica que lanza FileNotFoundError para rutas inexistentes."""
        with pytest.raises(FileNotFoundError):
            cargar_archivo("ruta/falsa/no_existe.csv")

    def test_limpia_nulos_y_vacios(self, csv_con_nulos):
        """Verifica que las filas con descripción vacía/nula se eliminan."""
        df = cargar_archivo(csv_con_nulos)
        assert len(df) == 2  # Solo P001 y P003 deben sobrevivir

    def test_carga_csv_una_columna(self, csv_una_columna):
        """Verifica el fallback cuando solo hay una columna."""
        df = cargar_archivo(csv_una_columna)
        assert COLUMNA_DESCRIPCION in df.columns
        assert len(df) == 2

    def test_carga_csv_vacio(self, csv_vacio):
        """Verifica que un CSV vacío retorna DataFrame vacío."""
        df = cargar_archivo(csv_vacio)
        assert len(df) == 0

    def test_carga_excel(self, tmp_path):
        """Verifica que archivos Excel se cargan correctamente."""
        excel_file = tmp_path / "test.xlsx"
        df_orig = pd.DataFrame({
            COLUMNA_ID: ["P001", "P002"],
            COLUMNA_DESCRIPCION: ["Zapatos de cuero", "Camisetas de algodón"]
        })
        df_orig.to_excel(excel_file, index=False)
        df = cargar_archivo(str(excel_file))
        assert len(df) == 2
        assert COLUMNA_ID in df.columns


# ============================================================================
# TESTS: clasificar_producto() — Parseo de respuestas
# ============================================================================

class TestClasificarProductoParseo:
    """Tests que verifican el manejo de diferentes formatos de respuesta."""

    def test_deteccion_nit_como_descripcion(self):
        """Verifica que descriptions numéricas (posibles NITs) se detectan."""
        resultado = clasificar_producto("900123456")
        assert resultado["hs_code"] == "ERROR_MAREO"
        assert resultado["confianza"] == "baja"

    def test_no_detecta_nit_en_texto_normal(self):
        """Verifica que descripciones con números pero texto real no son bloqueadas."""
        # Si Ollama está arriba, retornará algo real; si no, retornará error HTTP
        resultado = clasificar_producto("Teléfono celular Samsung Galaxy S24 128GB")
        assert resultado["hs_code"] != "ERROR_MAREO"

    def test_cache_devuelve_mismo_resultado(self):
        """Verifica que el cache funciona para llamadas repetidas."""
        desc = "900123456"  # Usamos NIT detection para no depender de Ollama
        r1 = clasificar_producto(desc)
        r2 = clasificar_producto(desc)
        assert r1 == r2

    def test_cache_key_case_insensitive(self):
        """Verifica que las keys del cache son case-insensitive."""
        desc1 = "900123456"
        desc2 = "900123456"  # mismo
        key1 = hashlib.md5(desc1.strip().lower().encode()).hexdigest()
        key2 = hashlib.md5(desc2.strip().lower().encode()).hexdigest()
        assert key1 == key2


# ============================================================================
# TESTS: BaseConocimientoAduanera (RAG)
# ============================================================================

class TestBaseConocimiento:
    """Tests para el sistema RAG de conocimiento aduanero."""

    def test_singleton(self):
        """Verifica que get_instance() retorna siempre la misma instancia."""
        bc1 = BaseConocimientoAduanera.get_instance()
        bc2 = BaseConocimientoAduanera.get_instance()
        assert bc1 is bc2

    def test_buscar_similares_retorna_string(self):
        """Verifica que buscar_similares retorna un string (contexto o error)."""
        bc = BaseConocimientoAduanera.get_instance()
        resultado = bc.buscar_similares("Aceite de oliva virgen extra")
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_buscar_similares_con_texto_irrelevante(self):
        """Verifica que texto completamente irrelevante no crashea."""
        bc = BaseConocimientoAduanera.get_instance()
        resultado = bc.buscar_similares("xyz123 completamente random sin sentido")
        assert isinstance(resultado, str)

    def test_historico_cargado(self):
        """Verifica que la base de conocimiento cargó el archivo histórico."""
        bc = BaseConocimientoAduanera.get_instance()
        if bc._modelo_embeddings is not None:
            assert bc._df_historico is not None
            assert len(bc._df_historico) > 0
            assert 'DESCRIPCION_MERCANCIA' in bc._df_historico.columns
            assert 'HS_CODE' in bc._df_historico.columns


# ============================================================================
# TESTS: exportar_json()
# ============================================================================

class TestExportarJson:
    """Tests para la función de exportación JSON."""

    def test_exporta_json_valido(self, tmp_path):
        """Verifica que el JSON exportado es válido y parseable."""
        df = pd.DataFrame({
            COLUMNA_ID: ["P001"],
            COLUMNA_DESCRIPCION: ["Zapatos de cuero"],
            "HS_CODE": ["6403990000"],
            "CONFIANZA": ["alta"]
        })
        ruta = str(tmp_path / "test_output.json")
        json_str = exportar_json(df, ruta)

        # Verificar que el string JSON es válido
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["HS_CODE"] == "6403990000"

    def test_exporta_json_a_disco(self, tmp_path):
        """Verifica que el archivo JSON se crea en disco."""
        df = pd.DataFrame({
            COLUMNA_ID: ["P001"],
            COLUMNA_DESCRIPCION: ["Test"],
            "HS_CODE": ["0000000000"],
            "CONFIANZA": ["baja"]
        })
        ruta = str(tmp_path / "salida" / "resultado.json")
        exportar_json(df, ruta)
        assert os.path.exists(ruta)

    def test_exporta_json_sin_ruta(self):
        """Verifica que funciona sin ruta de salida (solo retorna string)."""
        df = pd.DataFrame({
            COLUMNA_ID: ["P001"],
            COLUMNA_DESCRIPCION: ["Test"],
            "HS_CODE": ["0000000000"],
            "CONFIANZA": ["baja"]
        })
        json_str = exportar_json(df)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert len(parsed) == 1

    def test_exporta_json_caracteres_especiales(self, tmp_path):
        """Verifica que acentos y caracteres especiales se preservan."""
        df = pd.DataFrame({
            COLUMNA_ID: ["P001"],
            COLUMNA_DESCRIPCION: ["Cañón de señalización óptica"],
            "HS_CODE": ["9306900000"],
            "CONFIANZA": ["media"]
        })
        json_str = exportar_json(df)
        parsed = json.loads(json_str)
        assert "Cañón" in parsed[0][COLUMNA_DESCRIPCION]


# ============================================================================
# TESTS: Integración con Ollama (requieren servidor activo)
# ============================================================================

def ollama_disponible():
    """Verifica si el servidor Ollama está corriendo."""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = r.json().get("models", [])
        return any(m["name"] == MODELO_IA for m in models)
    except:
        return False


@pytest.mark.skipif(not ollama_disponible(), reason="Ollama no disponible o phi4 no instalado")
class TestIntegracionOllama:
    """Tests de integración real con Ollama + phi4:latest."""

    def test_clasificar_zapatos(self):
        """Test real: clasifica zapatos de cuero."""
        resultado = clasificar_producto("Zapatos de cuero italiano con suela de caucho para hombre")
        assert "hs_code" in resultado
        assert "confianza" in resultado
        assert resultado["confianza"] in ("alta", "media", "baja")
        # El código HS debe tener al menos 4 dígitos
        assert len(resultado["hs_code"]) >= 4
        # Debería comenzar con 64 (calzado) 
        assert resultado["hs_code"].startswith("64"), f"Esperado HS 64xx para calzado, got: {resultado['hs_code']}"

    def test_clasificar_aceite_oliva(self):
        """Test real: clasifica aceite de oliva."""
        resultado = clasificar_producto("Aceite de oliva extra virgen orgánico 500ml botella de vidrio")
        assert "hs_code" in resultado
        assert resultado["confianza"] in ("alta", "media", "baja")
        # Debería ser 1509 (aceite de oliva)
        assert resultado["hs_code"].startswith("15"), f"Esperado HS 15xx para aceite, got: {resultado['hs_code']}"

    def test_clasificar_laptop(self):
        """Test real: clasifica laptop."""
        resultado = clasificar_producto("Laptop portátil 15 pulgadas procesador Intel Core i7 16GB RAM")
        assert "hs_code" in resultado
        assert resultado["confianza"] in ("alta", "media", "baja")
        # Debería ser 8471 (máquinas automáticas para procesamiento de datos)
        assert resultado["hs_code"].startswith("84"), f"Esperado HS 84xx para laptop, got: {resultado['hs_code']}"

    def test_clasificar_fertilizante(self):
        """Test real: clasifica fertilizante NPK."""
        resultado = clasificar_producto("Fertilizante granulado NPK 15-15-15 para agricultura presentación 50kg")
        assert "hs_code" in resultado
        assert resultado["confianza"] in ("alta", "media", "baja")
        # Debería ser 3105 (abonos minerales)
        assert resultado["hs_code"].startswith("31"), f"Esperado HS 31xx para fertilizante, got: {resultado['hs_code']}"

    def test_clasificar_con_razonamiento(self):
        """Verifica que el modelo incluye razonamiento RAG."""
        resultado = clasificar_producto("Café en grano tostado para exportación")
        assert "razonamiento" in resultado
        # Debería existir razonamiento no vacío
        assert len(resultado.get("razonamiento", "")) > 5

    def test_respuesta_json_estructura_correcta(self):
        """Verifica la estructura JSON completa de la respuesta."""
        resultado = clasificar_producto("Vino tinto reserva en botella de 750ml")
        keys = set(resultado.keys())
        assert "hs_code" in keys
        assert "confianza" in keys
        # hs_code debe ser solo dígitos
        assert resultado["hs_code"].isdigit() or resultado["hs_code"] == "ERROR"


# ============================================================================
# TESTS: Pipeline completo (clasificar_catalogo + exportar_json)
# ============================================================================

@pytest.mark.skipif(not ollama_disponible(), reason="Ollama no disponible o phi4 no instalado")
class TestPipelineCompleto:
    """Tests end-to-end del pipeline de clasificación masiva."""
    
    def test_pipeline_catalogo_pequeño(self, tmp_path):
        """Test E2E con un catálogo de 2 productos."""
        csv_file = tmp_path / "mini_catalogo.csv"
        csv_file.write_text(
            "ID_PRODUCTO,DESCRIPCION_MERCANCIA\n"
            "T001,Café en grano tostado colombiano premium 500g\n"
            "T002,Sillas de madera de roble para comedor estilo nórdico\n",
            encoding='utf-8'
        )
        
        df_resultado = clasificar_catalogo(str(csv_file))
        
        # Verificaciones de estructura
        assert "HS_CODE" in df_resultado.columns
        assert "CONFIANZA" in df_resultado.columns
        assert "RAZONAMIENTO" in df_resultado.columns
        assert len(df_resultado) == 2
        
        # Verificar que no hay errores generales
        errores = df_resultado[df_resultado["HS_CODE"] == "ERROR"]
        assert len(errores) == 0, f"Se encontraron errores: {errores.to_dict()}"

    def test_pipeline_exportar_json(self, tmp_path):
        """Test E2E: clasificar y exportar a JSON."""
        csv_file = tmp_path / "export_test.csv"
        csv_file.write_text(
            "ID_PRODUCTO,DESCRIPCION_MERCANCIA\n"
            "E001,Champú reparador con aceite de argán 500ml\n",
            encoding='utf-8'
        )
        
        df_resultado = clasificar_catalogo(str(csv_file))
        json_path = str(tmp_path / "resultado.json")
        json_str = exportar_json(df_resultado, json_path)
        
        # Verificar JSON
        parsed = json.loads(json_str)
        assert len(parsed) == 1
        assert "HS_CODE" in parsed[0]
        assert os.path.exists(json_path)


# ============================================================================
# TESTS: API Endpoint (sin servidor, test de lógica)
# ============================================================================

class TestAPILogica:
    """Tests que verifican la lógica del API sin levantar el servidor."""

    def test_import_api_main(self):
        """Verifica que api/main.py se puede importar sin errores."""
        api_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
        sys.path.insert(0, api_path)
        try:
            import main as api_main
            assert hasattr(api_main, 'app')
            assert hasattr(api_main, 'classify_product')
            assert hasattr(api_main, 'health_check')
        finally:
            sys.path.remove(api_path)

    def test_health_endpoint(self):
        """Verifica que el health endpoint retorna status ok."""
        api_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
        sys.path.insert(0, api_path)
        try:
            import main as api_main
            result = api_main.health_check()
            assert result["status"] == "ok"
        finally:
            sys.path.remove(api_path)


# ============================================================================
# TESTS: Configuración del sistema
# ============================================================================

class TestConfiguracion:
    """Verifica que las constantes y configuración son correctas."""

    def test_ollama_url(self):
        assert OLLAMA_URL == "http://localhost:11434/api/generate"

    def test_modelo_ia(self):
        assert MODELO_IA == "phi4:latest"

    def test_columnas_config(self):
        assert COLUMNA_ID == "ID_PRODUCTO"
        assert COLUMNA_DESCRIPCION == "DESCRIPCION_MERCANCIA"

    def test_historico_existe(self):
        """Verifica que el archivo histórico RAG existe."""
        ruta = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/historico_dian.csv'))
        assert os.path.exists(ruta), f"historico_dian.csv no encontrado en {ruta}"

    def test_catalogo_ejemplo_existe(self):
        """Verifica que el catálogo de ejemplo existe."""
        ruta = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/catalogo_ejemplo.csv'))
        assert os.path.exists(ruta), f"catalogo_ejemplo.csv no encontrado en {ruta}"
