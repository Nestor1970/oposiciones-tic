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
                   r"\btic\b", r"\bsistemas de información\b", r"\bdixital\b", r"\bdigital\b", r"\bredes\b",
                   r"\btecnoloxía da información\b", r"\btecnología de la información\b"]

    terminos_genericos = [r"\bcuerpos y escalas\b", r"\bcorpos e escalas\b", r"\boferta de empleo público\b", 
                          r"\boferta de emprego público\b", r"\boep\b", r"\bcorpo superior\b", r"\bcuerpo superior\b",
                          r"\bescala de sistemas\b"]
    
    accion = ["convoca", "proceso selectivo", "oposición", "libre", "quenda", "prazas", "ingreso", "plazas",
              "estabilización", "oferta de empleo", "oep", "oferta de emprego", "personal laboral", "funcionario"]
              
    doc = Document()
    doc.add_heading(f'Boletín de Oposiciones - {hoy.strftime("%d/%m/%Y")}', 0)
    anuncios_tic_directos = {} 
    anuncios_posibles = {}
    total_llamadas_proxy = 0
    
    print(f"\n--- 🛰️  BÚSQUEDA TIC + REDES ---")
    
    sesion = requests.Session()
    sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})

    for i in range(4):
        fecha = hoy - timedelta(days=i)
        f_str = fecha.strftime("%d/%m/%Y")
        print(f"🔍 Analizando {f_str}...")
        
        dia_semana = fecha.weekday() 
        urls = {}
        
        # 1. Configurar BOE y BOP (excluyendo fines de semana donde proceda)
        if dia_semana != 6: 
            urls["BOE"] = fecha.strftime("https://www.boe.es/boe/dias/%Y/%m/%d/")
        if dia_semana not in [5, 6]: 
            urls["BOP Coruña"] = f"https://bop.dacoruna.gal/bopportal/cambioBoletin.do?fechaInput={f_str}"
        
        # 2. Configurar DOG (Fuerza Bruta: Secciones de la 1 a la 6)
        for sec in range(1, 6):
            urls[f"DOG Sec {sec}"] = f"https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?ruta=/{fecha.year}/{fecha.strftime('%Y%m%d')}/Secciones{sec}_gl.html"
        
        # 3. Procesar todas las URLs del día
        for fuente, url in urls.items():
            try:
                if (fuente.startswith("DOG") or fuente == "BOE") and api_key_proxy:
                    total_llamadas_proxy += 1
                    res = requests.get(f"http://api.scraperapi.com?api_key={api_key_proxy}&url={quote(url, safe='')}&render=false", timeout=45) 
                else:
                    res = sesion.get(url, timeout=20)
                
                if res.status_code != 200: 
                    continue # Si la sección no existe ese día, simplemente la saltamos
                    
                sopa = BeautifulSoup(res.text, 'html.parser')
                elementos_analizar = []
                
                # --- EXTRACCIÓN BOP ---
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
                
                # --- EXTRACCIÓN DOG Y BOE ---
                else:
                    for item in sopa.find_all(['li', 'p']):
                        link = item.find('a', href=True)
                        if link:
                            elementos_analizar.append((item.get_text(separator=" "), urljoin(url, link['href'])))

                # --- FILTRADO Y CLASIFICACIÓN ---
                for texto, url_final in elementos_analizar:
                    texto_limpio = texto.strip()
                    if len(texto_limpio) < 15: continue 
                    txt_min = texto_limpio.lower()
                    
                    if (any(re.search(t, txt_min) for t in terminos_it) or any(re.search(g, txt_min) for g in terminos_genericos)) and any(a in txt_min for a in accion):
                        datos = {'texto': texto_limpio, 'fuente': fuente, 'fecha': f_str, 'url': url_final}
                        huella = re.sub(r'\W+', '', texto_limpio)[:200]
                        if any(re.search(t, txt_min) for t in terminos_it): 
                            anuncios_tic_directos[huella] = datos
                        else: 
                            anuncios_posibles[huella] = datos
            except Exception: 
                continue

    # --- GENERACIÓN DEL DOCUMENTO WORD ---
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
