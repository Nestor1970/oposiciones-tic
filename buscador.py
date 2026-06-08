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
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES: ÚLTIMOS 7 DÍAS ---")

    # LISTA A: Filtros IT + Redes (Palabra completa)
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b"]
    
    # LISTA B: Convocatorias
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "ferrol"]

    doc = Document()
    doc.add_heading(f'Oposiciones TIC y Redes - {datetime.now().strftime("%d/%m/%Y")}', 0)
    
    anuncios_finales = {} 
    hoy = datetime.now()

    # 2. RANGO DE 7 DÍAS CORREGIDO (Cambia a 15 si deseas ampliar el reporte)
    for i in range(7):
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

                # Cambiado a lxml para evitar saltos en estructuras complejas
                sopa = BeautifulSoup(res.text, 'lxml')
                for item in sopa.find_all(['li', 'p', 'tr', 'td']):
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

                        # Huella para evitar duplicados del mismo día
                        base_titulo = re.split(r'pdf|págs|otros formatos', txt_min, flags=re.IGNORECASE)[0]
                        huella = re.sub(r'\W+', '', base_titulo)[:200]

                        # Quitamos la dependencia de leidos.txt para que se mantengan durante los 7 días en el reporte
                        tiene_pdf = "pdf" in txt_min
                        if huella not in anuncios_finales or (tiene_pdf and "pdf" not in anuncios_finales[huella]['texto'].lower()):
                            anuncios_finales[huella] = {
                                'texto': texto, 'fuente': fuente, 'fecha': f_str, 'url': url
                            }
            except: 
                continue

    # 3. Escritura del archivo Word (Garantiza que siempre guarde aunque esté vacío, evitando correos rotos)
    if anuncios_finales:
        for huella, d in anuncios_finales.items():
            p = doc.add_paragraph()
            p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
            doc.add_paragraph(d['texto'])
            doc.add_paragraph(f"🔗 {d['url']}")
            doc.add_paragraph("-" * 30)
        print(f"\n\n✅ ¡Hecho! {len(anuncios_finales)} resultados agregados al informe semanal.")
    else:
        doc.add_paragraph("\nℹ️ No se han encontrado anuncios en la última semana bajo los criterios establecidos.")
        print(f"\n\nℹ️ Generando informe vacío preventivo.")

    # Salvamos SIEMPRE el documento para asegurar el adjunto en el flujo automatizado
    doc.save(nombre_word)

if __name__ == "__main__":
    rastreador_7_dias()
