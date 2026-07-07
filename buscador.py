import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document
from urllib.parse import quote, urljoin

def rastreador_7_dias_definitivo_v2():
    directorio = os.path.dirname(os.path.abspath(__file__))
    
    hoy = datetime.utcnow() + timedelta(hours=2) 
    fecha_hoy_str = hoy.strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    
    api_key_proxy = os.environ.get("SCRAPER_API_KEY")
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES (Motor BOP Inteligente) ---")
    
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b"]
                   
    terminos_genericos = [r"\bcuerpos y escalas\b", r"\bcorpos e escalas\b", r"\boferta de empleo público\b", 
                          r"\boferta de emprego público\b", r"\boep\b"]
    
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "ferrol",
              "estabilización", "oferta de empleo", "oep", "oferta de emprego", "personal laboral", "funcionario"]
              
    doc = Document()
    doc.add_heading(f'Boletín de Oposiciones - {hoy.strftime("%d/%m/%Y")}', 0)
    
    anuncios_tic_directos = {} 
    anuncios_posibles = {}
    
    sesion = requests.Session()
    cabeceras = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }
    sesion.headers.update(cabeceras)

    for i in range(7):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        dia_semana = fecha.weekday() 
        
        urls = {}
        if dia_semana != 6:
            urls["BOE"] = fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/")
        if dia_semana not in [5, 6]:
            urls["BOP Coruña"] = f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}"
            
        urls["DOG (Sec 2)"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones2_gl.html"
        urls["DOG (Sec 3)"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones3_gl.html"
        
        print(f"🔎 Analizando {f_str}...", end="\r")
        
        for fuente, url in urls.items():
            try:
                if (fuente.startswith("DOG") or fuente == "BOE") and api_key_proxy:
                    url_codificada = quote(url, safe='')
                    url_peticion = f"http://api.scraperapi.com?api_key={api_key_proxy}&url={url_codificada}&render=false"
                    res = requests.get(url_peticion, timeout=45) 
                else:
                    res = sesion.get(url, timeout=20)
                
                if res.status_code != 200: 
                    continue
                    
                sopa = BeautifulSoup(res.text, 'html.parser')
                elementos_analizar = []
                
                if fuente == "BOE":
                    for li in sopa.find_all('li', class_='dispo'):
                        link_tag = li.find('a', href=True)
                        if link_tag:
                            url_directa = urljoin("https://www.boe.es", link_tag['href'])
                            elementos_analizar.append((li.get_text(separator=" "), url_directa))
                            
                elif fuente.startswith("DOG"):
                    for p_tag in sopa.find_all(['p', 'span']):
                        link_tag = p_tag.find('a', href=True) if hasattr(p_tag, 'find') else None
                        if not link_tag and p_tag.parent and p_tag.parent.name == 'a':
                            link_tag = p_tag.parent
                        if link_tag:
                            url_directa = urljoin("https://www.xunta.gal", link_tag['href'])
                            elementos_analizar.append((p_tag.get_text(separator=" "), url_directa))
                            
                elif fuente == "BOP Coruña":
                    # 🚀 NUEVO MOTOR DE LECTURA LINEAL (Adaptado a la imagen)
                    cabecera_1 = ""
                    cabecera_2 = ""
                    anuncio_pendiente = ""
                    
                    for nodo in sopa.find_all(['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'span']):
                        texto = nodo.get_text(separator=" ", strip=True)
                        if not texto: continue
                        
                        # 1. ¿Es la línea de enlaces (PDF | HTML)?
                        enlace_pdf = nodo.find('a', string=re.compile(r'PDF', re.IGNORECASE))
                        if enlace_pdf and anuncio_pendiente:
                            url_directa = urljoin("https://bop.dacoruna.gal", enlace_pdf['href'])
                            
                            # Formateamos el organismo (Ej: "Ferrol - Recursos Humanos")
                            if cabecera_1 and cabecera_2:
                                municipio = f"{cabecera_1} - {cabecera_2}"
                            elif cabecera_1:
                                municipio = cabecera_1
                            else:
                                municipio = "BOP Coruña"
                                
                            texto_final = f"🏢 {municipio} | {anuncio_pendiente}"
                            elementos_analizar.append((texto_final, url_directa))
                            anuncio_pendiente = "" # Limpiamos para el siguiente anuncio
                            continue
                            
                        # Si es solo la línea de texto "( PDF | HTML... )" sin enlace directo, la saltamos
                        if "( PDF" in texto or "(PDF" in texto:
                            continue
                            
                        # 2. ¿Es el texto del anuncio? (En el BOP empiezan por "Año/Número" ej: 2026/4441)
                        if re.match(r'^\d{4}/\d+', texto):
                            anuncio_pendiente = texto
                            
                        # 3. ¿Es una cabecera? (Texto corto, sin números de expediente, sin links)
                        elif len(texto) < 70 and not nodo.find('a'):
                            if anuncio_pendiente:
                                # Si ya teníamos un anuncio y aparece texto corto, es que pasamos a un pueblo nuevo
                                cabecera_1 = texto
                                cabecera_2 = ""
                                anuncio_pendiente = ""
                            else:
                                # Vamos guardando las cabeceras jerárquicamente
                                if not cabecera_1:
                                    cabecera_1 = texto
                                elif cabecera_1 and not cabecera_2:
                                    cabecera_2 = texto
                                else:
                                    # Si hay una tercera cabecera seguida, desplazamos la anterior
                                    cabecera_1 = cabecera_2
                                    cabecera_2 = texto

                # --- PROCESAMIENTO, FILTRADO Y CLASIFICACIÓN ---
                for texto, url_final_anuncio in elementos_analizar:
                    texto_limpio = texto.strip()
                    # Bajamos el límite a 40 para no perder anuncios del BOP que a veces son muy escuetos
                    if len(texto_limpio) < 40: continue 
                    
                    txt_min = texto_limpio.lower()
                    
                    tiene_it = any(re.search(t, txt_min) for t in terminos_it)
                    tiene_generico = any(re.search(g, txt_min) for g in terminos_genericos)
                    tiene_accion = any(a in txt_min for a in accion)
                    
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
                        
                        if tiene_it:
                            if huella not in anuncios_tic_directos or (tiene_pdf and "pdf" not in anuncios_tic_directos[huella]['texto'].lower()):
                                anuncios_tic_directos[huella] = datos_anuncio
                        elif tiene_generico:
                            if huella not in anuncios_posibles or (tiene_pdf and "pdf" not in anuncios_posibles[huella]['texto'].lower()):
                                anuncios_posibles[huella] = datos_anuncio
                                
            except Exception as e:
                continue

    # --- GENERACIÓN DEL DOCUMENTO WORD ---
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

    doc.add_heading('⚠️ Posibles Oposiciones (Convocatorias Generales)', level=1)
    if anuncios_posibles:
        doc.add_paragraph("Estos anuncios no mencionan puestos TIC explícitamente, pero son convocatorias abiertas donde podrían esconderse plazas:")
        for huella, d in anuncios_posibles.items():
            p = doc.add_paragraph()
            p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
            doc.add_paragraph(d['texto'])
            doc.add_paragraph(f"🔗 Enlace directo: {d['url']}")
            doc.add_paragraph("-" * 30)
    else:
        doc.add_paragraph("No se han detectado convocatorias generales en estos días.")

    print(f"\n\n✅ ¡Hecho! Encontrados {len(anuncios_tic_directos)} TIC directos y {len(anuncios_posibles)} posibles.")
    doc.save(nombre_word)

if __name__ == "__main__":
    rastreador_7_dias_definitivo_v2()
