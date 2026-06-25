import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document
from urllib.parse import quote, urljoin

def rastreador_7_dias_enlaces_directos():
    directorio = os.path.dirname(os.path.abspath(__file__))
    
    # Forzamos hora de España para que los saltos de día sean exactos
    hoy = datetime.utcnow() + timedelta(hours=2) 
    fecha_hoy_str = hoy.strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    
    api_key_proxy = os.environ.get("SCRAPER_API_KEY")
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES (Modo Enlaces Directos - 7 días) ---")
    
    # Términos tecnológicos habituales
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b"]
    
    # 🔥 AMPLIADO: Palabras clave de acción que capturan convocatorias generales o extractos escuetos
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "estatutario",
              "estabilización", "oferta de empleo", "oep", "oferta de emprego", "personal laboral", "funcionario"]
              
    doc = Document()
    doc.add_heading(f'Oposiciones TIC y Redes - {hoy.strftime("%d/%m/%Y")}', 0)
    anuncios_finales = {} 
    
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
        urls["DOG"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones3_gl.html"
        
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
                
                # 🛠️ NUEVA ESTRUCTURA DE EXTRACCIÓN POR FUENTE (Para sacar el link específico)
                elementos_analizar = []
                
                if fuente == "BOE":
                    # En el BOE, cada anuncio está dentro de un elemento 'li' con clase 'dispo'
                    for li in sopa.find_all('li', class_='dispo'):
                        link_tag = li.find('a', href=True)
                        if link_tag:
                            url_directa = urljoin("https://www.boe.es", link_tag['href'])
                            elementos_analizar.append((li.get_text(separator=" "), url_directa))
                            
                elif fuente == "DOG":
                    # En el DOG, los anuncios están en tablas o listas con enlaces de clase 'idAnuncio' o dentro de Secciones
                    for p_tag in sopa.find_all(['p', 'span']):
                        link_tag = p_tag.find('a', href=True) if hasattr(p_tag, 'find') else None
                        if not link_tag and p_tag.parent and p_tag.parent.name == 'a':
                            link_tag = p_tag.parent
                        if link_tag:
                            url_directa = urljoin("https://www.xunta.gal", link_tag['href'])
                            elementos_analizar.append((p_tag.get_text(separator=" "), url_directa))
                            
                elif fuente == "BOP Coruña":
                    # En el BOP, los anuncios suelen estar en bloques de texto con enlaces de descarga directa
                    for item in sopa.find_all(['li', 'p', 'tr']):
                        link_tag = item.find('a', href=True)
                        if link_tag:
                            url_directa = urljoin("https://bop.dacoruna.gal", link_tag['href'])
                            elementos_analizar.append((item.get_text(separator=" "), url_directa))

                # Si la extracción específica no devolvió nada, usamos el fallback clásico (por si acaso cambian el HTML)
                if not elementos_analizar:
                    for item in sopa.find_all(['li', 'p']):
                        texto = item.get_text(separator=" ").strip()
                        elementos_analizar.append((texto, url))

                # Procesamos y filtramos los textos obtenidos
                for texto, url_final_anuncio in elementos_analizar:
                    texto_limpio = texto.strip()
                    if len(texto_limpio) < 50: continue
                    
                    txt_min = texto_limpio.lower()
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
                                'texto': texto_limpio, 'fuente': fuente, 'fecha': f_str, 'url': url_final_anuncio
                            }
            except Exception as e:
                print(f"\n   ❌ Error en {fuente} ({f_str}): {e}")
                continue

    if anuncios_finales:
        for huella, d in anuncios_finales.items():
            p = doc.add_paragraph()
            p.add_run(f"📌 {d['fuente']} - {d['fecha']}").bold = True
            doc.add_paragraph(d['texto'])
            doc.add_paragraph(f"🔗 Enlace directo: {d['url']}")
            doc.add_paragraph("-" * 30)
        print(f"\n\n✅ ¡Hecho! {len(anuncios_finales)} resultados agregados al informe.")
    else:
        doc.add_paragraph("\nℹ️ No se han encontrado anuncios en el rango de días revisado.")
        print(f"\n\nℹ️ Generando informe vacío.")
        
    doc.save(nombre_word)

if __name__ == "__main__":
    rastreador_7_dias_enlaces_directos()
