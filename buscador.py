import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from docx import Document
from urllib.parse import quote, urljoin

def rastreador_7_dias_definitivo():
    directorio = os.getcwd()
    hoy = datetime.utcnow() + timedelta(hours=2) 
    fecha_hoy_str = hoy.strftime("%d_%m_%Y")
    nombre_word = os.path.join(directorio, f"Oposiciones_{fecha_hoy_str}.docx")
    api_key_proxy = os.environ.get("SCRAPER_API_KEY")
    
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
    total_llamadas_proxy = 0
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES ---")
    
    sesion = requests.Session()
    sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})

    for i in range(7):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        print(f"🔍 Analizando {f_str}...")
        
        dia_semana = fecha.weekday() 
        urls = {}
        if dia_semana != 6: urls["BOE"] = fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/")
        if dia_semana not in [5, 6]: urls["BOP Coruña"] = f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}"
        
        # --- LÓGICA INTELIGENTE DOG CORREGIDA ---
        url_indice = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Indice_gl.html"
        try:
            # CORRECCIÓN 1: Usar proxy también para el índice o GitHub será bloqueado por la Xunta
            if api_key_proxy:
                total_llamadas_proxy += 1
                req_url = f"http://api.scraperapi.com?api_key={api_key_proxy}&url={quote(url_indice, safe='')}&render=false"
                res_indice = requests.get(req_url, timeout=45)
            else:
                res_indice = sesion.get(url_indice, timeout=20)
                
            if res_indice.status_code == 200:
                sopa_indice = BeautifulSoup(res_indice.text, 'html.parser')
                for link in sopa_indice.find_all('a', href=True):
                    texto_link = link.get_text(strip=True)
                    # CORRECCIÓN 2: "Oposic" captura tanto "Oposiciones" (ES) como "Oposicións" (GL)
                    if "IV. Oposic" in texto_link or "VI. Anuncios" in texto_link:
                        urls[f"DOG {texto_link}"] = urljoin(url_indice, link['href'])
        except Exception:
            pass
        
        for fuente, url in urls.items():
            try:
                if (fuente.startswith("DOG") or fuente == "BOE") and api_key_proxy:
                    total_llamadas_proxy += 1
                    res = requests.get(f"http://api.scraperapi.com?api_key={api_key_proxy}&url={quote(url, safe='')}&render=false", timeout=45) 
                else:
                    res = sesion.get(url, timeout=20)
                
                if res.status_code != 200: continue
                    
                sopa = BeautifulSoup(res.text, 'html.parser')
                elementos_analizar = []
                
                if "BOP Coruña" in fuente:
                    for item in sopa.find_all(['li', 'p']):
                        link = item.find('a', href=True)
                        if link:
                            id_match = re.search(r'(\d{4}_\d+)', link['href'])
                            id_archivo = id_match.group(1) if id_match else "0000_0000"
                            u = f"https://bop.dacoruna.gal/bopportal/publicado/{fecha.strftime('%Y/%m/%d')}/{id_archivo}.pdf"
                            
                            texto_item = item.get_text(separator=" ")
                            municipio = "BOP Coruña"
                            prev_node = item.find_previous(['h1', 'h2', 'h3', 'p', 'div'])
                            if prev_node: municipio = prev_node.get_text(strip=True)
                            
                            elementos_analizar.append((f"🏢 {municipio} | {texto_item}", u))
                else:
                    for item in sopa.find_all(['li', 'p']):
                        link = item.find('a', href=True)
                        if link:
                            elementos_analizar.append((item.get_text(separator=" "), urljoin(url, link['href'])))

                for texto, url_final in elementos_analizar:
                    texto_limpio = texto.strip()
                    if len(texto_limpio) < 15: continue 
                    txt_min = texto_limpio.lower()
                    
                    if (any(re.search(t, txt_min) for t in terminos_it) or any(re.search(g, txt_min) for g in terminos_genericos)) and any(a in txt_min for a in accion):
                        datos = {'texto': texto_limpio, 'fuente': fuente, 'fecha': f_str, 'url': url_final}
                        huella = re.sub(r'\W+', '', texto_limpio)[:200]
                        if any(re.search(t, txt_min) for t in terminos_it): anuncios_tic_directos[huella] = datos
                        else: anuncios_posibles[huella] = datos
            except Exception: continue

    doc.add_heading('🎯 Búsqueda Directa (Puestos TIC)', level=1)
    for d in anuncios_tic_directos.values():
        doc.add_paragraph(f"{d['fuente']} - {d['fecha']}\n{d['texto']}\n🔗 {d['url']}\n" + "-"*30)
    
    doc.add_heading('⚠️ Posibles Oposiciones', level=1)
    for d in anuncios_posibles.values():
        doc.add_paragraph(f"{d['fuente']} - {d['fecha']}\n{d['texto']}\n🔗 {d['url']}\n" + "-"*30)
        
    doc.save(nombre_word)
    print(f"\n✅ ¡Hecho! Encontrados {len(anuncios_tic_directos)} TIC directos y {len(anuncios_posibles)} posibles. (Llamadas Proxy: {total_llamadas_proxy})")

if __name__ == "__main__":
    rastreador_7_dias_definitivo()
