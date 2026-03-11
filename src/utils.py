import re

def normalize_nit(raw_nit) -> str:
    """
    Normaliza un NIT colombiano a string de exactamente 9 dígitos.
    Elimina puntos, guiones, espacios y dígito verificador.
    Rellena con ceros a la izquierda si es necesario.
    
    Ejemplos:
        "900.123.456-7" -> "900123456"
        "12345678"      -> "012345678"
        900123456       -> "900123456"
    
    Raises:
        ValueError si el NIT tiene menos de 6 dígitos después de limpiar.
    """
    # Convert to string in case it's an int/float
    nit_str = str(raw_nit)
    
    # Remove anything that is not a digit or a hyphen
    nit_str = re.sub(r'[^\d-]', '', nit_str)
    
    # If there's a hyphen, take everything before it (removing the verification digit)
    if '-' in nit_str:
        nit_str = nit_str.split('-')[0]
        
    # Remove any remaining non-digit characters (should just be empty space)
    nit_str = re.sub(r'\D', '', nit_str)
    
    # Check if length is less than 6
    if len(nit_str) < 6:
        raise ValueError(f"NIT too short after cleaning: {raw_nit} -> {nit_str}")
        
    # Pad with leading zeros to make it exactly 9 digits
    nit_str = nit_str.zfill(9)
    
    # If it's longer than 9 digits (which shouldn't happen with valid NITs, but just in case)
    # the prompt specifies "exactamente 9 dígitos", so we only take the last 9 digits.
    # We will assume that if someone passes a 10 digit, it's either wrong or we shouldn't truncate.
    # It's safer to just return the zfilled string, but if over 9, let's keep it as is, or raise an error?
    # Actually, Colombian NITs usually don't exceed 9 digits. Let's just return what we have.
    # The prompt says "Normaliza un NIT colombiano a string de exactamente 9 dígitos."
    if len(nit_str) > 9:
        nit_str = nit_str[-9:] # If by some reason it is longer, take last 9 or raise. Taking last 9.
    
    return nit_str
