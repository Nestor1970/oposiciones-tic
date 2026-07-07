import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document
from urllib.parse import quote, urljoin

def rastreador_7_dias_dos_listas():
    directorio = os.path.dirname(os.path.abspath(__file__))
    
    hoy = datetime.utcnow() + timedelta(hours=2) 
    fecha_hoy_str = hoy.strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    
    api_key_proxy = os.environ.get("SCRAPER_API_KEY")
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES (Modo 2 Listas Inteligentes) ---")
    
    # 🎯 LISTA 1: Términos 100% tecnológicos
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b"]
                   
    # ⚠️ LISTA 2: Términos genéricos que suelen esconder plazas
    terminos_genericos = [r"\bcuerpos y escalas\b", r"\bcorpos e escalas\b", r"\boferta de empleo público\b", 
                          r"\boferta de emprego público\b", r"\boep\b"]
    
    # Términos de acción (obligatorios para ambas listas)
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "ferrol",
              "estabilización", "oferta de empleo", "oep", "oferta de emprego", "personal laboral", "funcionario"]
              
    doc = Document()
    doc.add_heading(f'Boletín de Oposiciones - {hoy.strftime("%d/%m/%Y")}', 0)
    
    # Separamos en dos diccionarios distintos
    anuncios_tic_directos = {} 
    anuncios_posibles = {}
    
    sesion = requests.Session()
    cabeceras = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }
    sesion.headers.update(cabeceras)

    # El bucle recorre de hoy (i=0) hacia atrás (i=6), lo que garantiza el orden más nuevo -> más antiguo
    for i in range(7):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        dia_semana = fecha.weekday() 
        
        urls = {}
        if dia_semana != 6:
            urls["BOE"] = fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/")
        if dia_semana not in [5, 6]:
            urls["BOP Coruña"] = f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}"
        urls["DOG"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones2_es.html"
        
        print(f"🔎 Analizando {f_str}...", end="\r")
        
        for fuente, url in urls.items():
            try:
                if fuente in ["DOG", "BOE"] and api_key_proxy:
                    url_codificada = quote(url, safe='')
                    url_peticion = f"http://api.scraperapi.com?api_key={api_key_proxy}&url={url_codificada}&render=false"
                    res = requests.get(url_peticion, timeout=45) 
                else:
                    res = sesion.get(url, timeout=20)
                
                if res.status_code != 200: 
                    continue
                    
                sopa = BeautifulSoup(res.text, 'html.parser')
                elementos_analizar = []
                
                # Extracción de enlaces directos (igual que en la versión anterior)
                if fuente == "BOE":
                    for li in sopa.find_all('li', class_='dispo'):
                        link_tag = li.find('a', href=True)
                        if link_tag:
                            url_directa = urljoin("https://www.boe.es", link_tag['href'])
                            elementos_analizar.append((li.get_text(separator=" "), url_directa))
                elif fuente == "DOG":
                    for p_tag in sopa.find_all(['p', 'span']):
                        link_tag = p_tag.find('a', href=True) if hasattr(p_tag, 'find') else None
                        if not link_tag and p_tag.parent and p_tag.parent.name == 'a':
                            link_tag = p_tag.parent
                        if link_tag:
                            url_directa = urljoin("https://www.xunta.gal", link_tag['href'])
                            elementos_analizar.append((p_tag.get_text(separator=" "), url_directa))
                elif fuente == "BOP Coruña":
                    for item in sopa.find_all(['li', 'p', 'tr']):
                        link_tag = item.find('a', href=True)
                        if link_tag:
                            url_directa = urljoin("https://bop.dacoruna.gal", link_tag['href'])
                            elementos_analizar.append((item.get_text(separator=" "), url_directa))

                if not elementos_analizar:
                    for item in sopa.find_all(['li', 'p']):
                        texto = item.get_text(separator=" ").strip()
                        elementos_analizar.append((texto, url))

                # PROCESAMIENTO Y CLASIFICACIÓN EN 1 SOLA PASADA
                for texto, url_final_anuncio in elementos_analizar:
                    texto_limpio = texto.strip()
                    if len(texto_limpio) < 50: continue
                    
                    txt_min = texto_limpio.lower()
                    
                    # Evaluamos a qué grupo pertenece
                    tiene_it = any(re.search(t, txt_min) for t in terminos_it)
                    tiene_generico = any(re.search(g, txt_min) for g in terminos_genericos)
                    tiene_accion = any(a in txt_min for a in accion)
                    
                    # Si cumple con alguna de las dos casuísticas y es una acción válida...
                    if (tiene_it or tiene_generico) and tiene_accion:
                        es_concurso_interno = any(c in txt_min for c in ["concurso específico", "concurso de traslados", "provisión de puestos"])
                        es_libre = any(l in txt_min for l in ["libre", "oposición", "quenda"])
                        
                        if es_concurso_interno and not es_libre:
                            continue
                            
                        base_titulo = re.split(r'pdf|págs|otros formatos', txt_min, flags=re.IGNORECASE)[0]
                        huella = re.sub(r'\W+', '', base_titulo)[:200]
                        tiene_pdf = "pdf" in txt_min
                        
                        datos_anuncio = {
                            'texto': texto_limpio, 'fuente': fuente, 'fecha': f_str, 'url': url_final_anuncio
                        }
                        
                        # 🛤️ BIFURCACIÓN INTELIGENTE (Prioridad a TIC)
                        if tiene_it:
                            if huella not in anuncios_tic_directos or (tiene_pdf and "pdf" not in anuncios_tic_directos[huella]['texto'].lower()):
                                anuncios_tic_directos[huella] = datos_anuncio
                        elif tiene_generico:
                            if huella not in anuncios_posibles or (tiene_pdf and "pdf" not in anuncios_posibles[huella]['texto'].lower()):
                                anuncios_posibles[huella] = datos_anuncio
                                
            except Exception as e:
                continue

    # --- GENERACIÓN DEL DOCUMENTO WORD ---
    
    # SECCIÓN 1: Anuncios TIC Directos
    doc.add_heading('🎯 Búsqueda Directa (Puestos TIC)', level=1)
    if anuncios_tic_directos:
        for huella, d in anuncios_tic_directos.items():
            p = doc.add_paragraph()
            p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
            doc.add_paragraph(d['texto'])
            doc.add_paragraph(f"🔗 Enlace directo: {d['url']}")
            doc.add_paragraph("-" * 30)
    else:
        doc.add_paragraph("No hay anuncios TIC directos en estos días.")

    # SECCIÓN 2: Posibles (Convocatorias Generales)
    doc.add_heading('⚠️ Posibles Oposiciones (Convocatorias Generales)', level=1)
    if anuncios_posibles:
        doc.add_paragraph("Estos anuncios no mencionan puestos TIC explícitamente, pero son convocatorias abiertas donde podrían esconderse plazas. Échales un ojo:")
        for huella, d in anuncios_posibles.items():
            p = doc.add_paragraph()
            p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
            doc.add_paragraph(d['texto'])
            doc.add_paragraph(f"🔗 Enlace directo: {d['url']}")
            doc.add_paragraph("-" * 30)
    else:
        doc.add_paragraph("No se han detectado convocatorias generales en estos días.")

    # Guardado final
    print(f"\n\n✅ ¡Hecho! Encontrados {len(anuncios_tic_directos)} TIC directos y {len(anuncios_posibles)} posibles.")
    doc.save(nombre_word)

if __name__ == "__main__":
    rastreador_7_dias_dos_listas()
