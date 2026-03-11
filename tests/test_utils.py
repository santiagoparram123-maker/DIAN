import pytest
import sys
import os

# Add the src directory to the python path so we can import utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils import normalize_nit

def test_normalize_nit_with_dots_and_hyphen():
    assert normalize_nit("900.123.456-7") == "900123456"

def test_normalize_nit_without_verification_digit():
    assert normalize_nit("900123456") == "900123456"

def test_normalize_nit_short_pads_with_zeros():
    assert normalize_nit("12345678") == "012345678"
    assert normalize_nit("123456") == "000123456"

def test_normalize_nit_as_integer():
    assert normalize_nit(900123456) == "900123456"
    assert normalize_nit(12345678) == "012345678"

def test_normalize_nit_already_normalized():
    assert normalize_nit("900123456") == "900123456"
    assert normalize_nit("012345678") == "012345678"

def test_normalize_nit_too_short_raises_value_error():
    with pytest.raises(ValueError):
        normalize_nit("12345")
    
    with pytest.raises(ValueError):
        normalize_nit("12.3-4")

def test_normalize_nit_with_spaces():
    assert normalize_nit(" 900 123 456 - 7 ") == "900123456"
