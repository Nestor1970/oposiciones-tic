import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document

def rastreador_15_dias():
    # Aseguramos el uso correcto de __file__
    directorio = os.path.dirname(os.path.abspath(__file__))
    
    # Forzamos hora de España para que los saltos de día sean exactos
    hoy = datetime.utcnow() + timedelta(hours=2) 
    fecha_hoy_str = hoy.strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES ---")
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b"]
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "ferrol"]
    
    doc = Document()
    doc.add_heading(f'Oposiciones TIC y Redes - {hoy.strftime("%d/%m/%Y")}', 0)
    anuncios_finales = {} 
    
    # 🔥 Ampliado a 15 días según lo solicitado
    for i in range(15):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        
        urls = {
            "BOE": fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/"),
            "BOP Coruña": f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}",
            "DOG": f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones3_gl.html"
        }
        
        print(f"🔎 Analizando {f_str}...", end="\r")
        
        cabeceras = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9'
        }
        
        for fuente, url in urls.items():
            try:
                res = requests.get(url, timeout=20, headers=cabeceras)
                
                if res.status_code != 200: 
                    print(f"\n   ⚠️ Bloqueo HTTP {res.status_code} en {fuente} el día {f_str}")
                    continue
                    
                sopa = BeautifulSoup(res.text, 'html.parser')
                for item in sopa.find_all(['li', 'p']):
                    texto = item.get_text(separator=" ").strip()
                    if len(texto) < 50: continue
                    
                    txt_min = texto.lower()
                    tiene_it_redes = any(re.search(t, txt_min) for t in terminos_it)
                    tiene_accion = any(a in txt_min for a in accion)
                    
                    if tiene_it_redes and tiene_accion:
                        es_concurso_interno = any(c in txt_min for c in ["concurso específico", "concurso de traslados", "provisión de puestos"])
                        es_libre = any(l in txt_min for l in ["libre", "oposición", "quenda"])
                        
                        if es_concurso_interno and not es_libre:
                            continue
                            
                        base_titulo = re.split(r'pdf|págs|otros formatos', txt_min, flags=re.IGNORECASE)[0]
                        huella = re.sub(r'\W+', '', base_titulo)[:200]
                        tiene_pdf = "pdf" in txt_min
                        
                        if huella not in anuncios_finales or (tiene_pdf and "pdf" not in anuncios_finales[huella]['texto'].lower()):
                            anuncios_finales[huella] = {
                                'texto': texto, 'fuente': fuente, 'fecha': f_str, 'url': url
                            }
            except Exception as e:
                # 🔥 AHORA SÍ VEREMOS EL ERROR: Imprimimos la excepción en lugar de silenciarla
                print(f"\n   ❌ Error crítico en {fuente} ({f_str}): {e}")
                continue

    if anuncios_finales:
        for huella, d in anuncios_finales.items():
            p = doc.add_paragraph()
            p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
            doc.add_paragraph(d['texto'])
            doc.add_paragraph(f"🔗 {d['url']}")
            doc.add_paragraph("-" * 30)
        print(f"\n\n✅ ¡Hecho! {len(anuncios_finales)} resultados agregados al informe.")
    else:
        doc.add_paragraph("\nℹ️ No se han encontrado anuncios en el rango de días revisado.")
        print(f"\n\nℹ️ Generando informe vacío.")
        
    doc.save(nombre_word)

if __name__ == "__main__":
    rastreador_15_dias()
