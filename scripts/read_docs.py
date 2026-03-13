import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

def read_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        texts = []
        for p in tree.iter('{' + ns['w'] + '}p'):
            texts.append(''.join(node.text for node in p.iter('{' + ns['w'] + '}t') if node.text))
        return '\n'.join(texts)
    except Exception as e:
        return f"Error reading DOCX: {e}"

out = open(r"C:\Users\santi\Documents\Santiago\CD\proyectos\DIAN\docs_output.txt", "w", encoding="utf-8")
out.write("--- DOCX CONTENT ---\n")
out.write(read_docx(r"C:\Users\santi\Documents\Santiago\CD\proyectos\DIAN\PDR_Auditor_DIAN.docx"))

try:
    out.write("\n\n--- XLSX CONTENT (Head) ---\n")
    df = pd.read_excel(r"C:\Users\santi\Documents\Santiago\CD\proyectos\DIAN\Proveedores-Ficticios-16022026.xlsx")
    out.write(df.head(20).to_string())
    out.write("\n\nColumnas:\n")
    out.write(str(df.columns.tolist()))
except Exception as e:
    out.write("\nError reading XLSX: " + str(e))

out.close()
