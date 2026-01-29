import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document

def rastreador_7_dias():
    # 1. Configuración de rutas y nombres
    directorio = os.path.dirname(os.path.abspath(__file__))
    fecha_hoy_str = datetime.now().strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    archivo_vistos = os.path.join(directorio, "leidos.txt")
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES: 7 DÍAS ---")

    # LISTA A: Filtros IT + Redes (Palabra completa)
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bredes\b"]
    
    # LISTA B: Convocatorias
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "Ferrol"]

    if not os.path.exists(archivo_vistos):
        open(archivo_vistos, 'w', encoding='utf-8').close()
    
    with open(archivo_vistos, 'r', encoding='utf-8') as f:
        vistos_historicos = set(line.strip() for line in f)

    doc = Document()
    doc.add_heading(f'Oposiciones TIC y Redes - {datetime.now().strftime("%d/%m/%Y")}', 0)
    
    anuncios_finales = {} 
    hoy = datetime.now()

    # 2. RANGO DE 7 DÍAS (de i=0 a i=6)
    for i in range(15):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        
        urls = {
            "BOE": fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/"),
            "BOP Coruña": f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}",
            "DOG": f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones3_gl.html"
        }

        print(f"🔎 Analizando {f_str}...", end="\r")

        for fuente, url in urls.items():
            try:
                res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if res.status_code != 200: continue

                sopa = BeautifulSoup(res.text, 'html.parser')
                for item in sopa.find_all(['li', 'p']):
                    texto = item.get_text(separator=" ").strip()
                    if len(texto) < 50: continue
                    
                    txt_min = texto.lower()

                    # Validar filtros
                    tiene_it_redes = any(re.search(t, txt_min) for t in terminos_it)
                    tiene_accion = any(a in txt_min for a in accion)

                    if tiene_it_redes and tiene_accion:
                        # Excluir solo concursos internos puros
                        es_concurso_interno = any(c in txt_min for c in ["concurso específico", "concurso de traslados", "provisión de puestos"])
                        es_libre = any(l in txt_min for l in ["libre", "oposición", "quenda"])
                        
                        if es_concurso_interno and not es_libre:
                            continue

                        # Huella para evitar duplicados técnicos
                        base_titulo = re.split(r'pdf|págs|otros formatos', txt_min, flags=re.IGNORECASE)[0]
                        huella = re.sub(r'\W+', '', base_titulo)[:200]

                        if huella not in vistos_historicos:
                            tiene_pdf = "pdf" in txt_min
                            # Si ya existe esta huella pero esta línea tiene el PDF, la guardamos
                            if huella not in anuncios_finales or (tiene_pdf and "pdf" not in anuncios_finales[huella]['texto'].lower()):
                                anuncios_finales[huella] = {
                                    'texto': texto, 'fuente': fuente, 'fecha': f_str, 'url': url
                                }
            except: continue

    # 3. Escritura del archivo
    for huella, d in anuncios_finales.items():
        p = doc.add_paragraph()
        p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
        doc.add_paragraph(d['texto'])
        doc.add_paragraph(f"🔗 {d['url']}")
        doc.add_paragraph("-" * 30)
        
        with open(archivo_vistos, 'a', encoding='utf-8') as f:
            f.write(huella + "\n")

    if anuncios_finales:
        doc.save(nombre_word)
        print(f"\n\n✅ ¡Hecho! Se han guardado {len(anuncios_finales)} resultados en '{os.path.basename(nombre_word)}'.")
    else:
        print(f"\n\nℹ️ No se han encontrado anuncios nuevos en los últimos 7 días.")

if __name__ == "__main__":
    rastreador_7_dias()

