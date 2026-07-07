import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document
from urllib.parse import quote, urljoin

def rastreador_7_dias_completo():
    directorio = os.path.dirname(os.path.abspath(__file__))
    hoy = datetime.utcnow() + timedelta(hours=2) 
    fecha_hoy_str = hoy.strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    api_key_proxy = os.environ.get("SCRAPER_API_KEY")
    
    # Términos originales
    terminos_it = [r"\binformática\b", r"\binformático\b", r"\bprogramador\b", r"\bsoftware\b", 
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b"]
    terminos_genericos = [r"\bcuerpos y escalas\b", r"\bcorpos e escalas\b", r"\boferta de empleo público\b", 
                          r"\boferta de emprego público\b", r"\boep\b"]
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "plazas",
              "estabilización", "oferta de empleo", "oep", "oferta de emprego", "personal laboral", "funcionario"]
              
    doc = Document()
    doc.add_heading(f'Boletín de Oposiciones - {hoy.strftime("%d/%m/%Y")}', 0)
    anuncios_tic_directos = {} 
    anuncios_posibles = {}
    
    sesion = requests.Session()
    sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})

    for i in range(7):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        dia_semana = fecha.weekday() 
        urls = {}
        if dia_semana != 6: urls["BOE"] = fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/")
        if dia_semana not in [5, 6]: urls["BOP Coruña"] = f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}"
        
        # MEJORA 1: Ambas secciones del DOG
        urls["DOG Sec 2"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones2_gl.html"
        urls["DOG Sec 3"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones3_gl.html"
        
        for fuente, url in urls.items():
            try:
                if (fuente.startswith("DOG") or fuente == "BOE") and api_key_proxy:
                    res = requests.get(f"http://api.scraperapi.com?api_key={api_key_proxy}&url={quote(url, safe='')}&render=false", timeout=45) 
                else:
                    res = sesion.get(url, timeout=20)
                
                if res.status_code != 200: continue
                    
                sopa = BeautifulSoup(res.text, 'html.parser')
                elementos_analizar = []
                
                # MEJORA 2: BOP con captura de cabeceras
                if fuente == "BOP Coruña":
                    for link in sopa.find_all('a', href=True):
                        if 'publicado' in link['href'] or link['href'].endswith('.pdf'):
                            u = urljoin("https://bop.dacoruna.gal", link['href']).replace('.html', '.pdf')
                            cabecera = ""
                            prev = link.find_previous(['p', 'h3', 'div'])
                            if prev: cabecera = prev.get_text(strip=True)
                            texto_anuncio = f"🏢 {cabecera} | {link.get_text(strip=True)}"
                            elementos_analizar.append((texto_anuncio, u))
                else:
                    for item in sopa.find_all(['li', 'p']):
                        link = item.find('a', href=True)
                        if link:
                            u = urljoin(url, link['href'])
                            elementos_analizar.append((item.get_text(separator=" "), u))

                for texto, url_final in elementos_analizar:
                    texto_limpio = texto.strip()
                    if len(texto_limpio) < 50: continue
                    txt_min = texto_limpio.lower()
                    
                    tiene_it = any(re.search(t, txt_min) for t in terminos_it)
                    tiene_generico = any(re.search(g, txt_min) for g in terminos_genericos)
                    tiene_accion = any(a in txt_min for a in accion)
                    
                    if (tiene_it or tiene_generico) and tiene_accion:
                        datos = {'texto': texto_limpio, 'fuente': fuente, 'fecha': f_str, 'url': url_final}
                        huella = re.sub(r'\W+', '', texto_limpio)[:200]
                        if tiene_it: anuncios_tic_directos[huella] = datos
                        elif tiene_generico: anuncios_posibles[huella] = datos
            except Exception: continue

    # Generación Word
    doc.add_heading('🎯 Búsqueda Directa (Puestos TIC)', level=1)
    for d in anuncios_tic_directos.values():
        doc.add_paragraph(f"{d['fuente']} - {d['fecha']}\n{d['texto']}\n🔗 {d['url']}\n" + "-"*30)
    
    doc.add_heading('⚠️ Posibles Oposiciones', level=1)
    for d in anuncios_posibles.values():
        doc.add_paragraph(f"{d['fuente']} - {d['fecha']}\n{d['texto']}\n🔗 {d['url']}\n" + "-"*30)
        
    doc.save(nombre_word)

if __name__ == "__main__":
    rastreador_7_dias_completo()
