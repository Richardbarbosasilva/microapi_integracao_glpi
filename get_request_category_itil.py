#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protótipo de micro API de integração GLPI Manutenção e GLPI TI
Exporta tickets fechados da categoria (STRING de categoria completa) para JSON.
"""

import requests
import json
import time
import os
from pathlib import Path

# === CONFIGURAÇÃO ===

GLPI_API_URL = "http://glpi-manutencao.clickip.local:5071/apirest.php"
APP_TOKEN = "eYoExwDP3ghgK7VlM0e5XYiggsU987A97OtsC1KO"   # substituir
USER_TOKEN = "ztOUa4e2HJhB7BMinpqHLgQSe1sx9rKUYmAaHmip"  # substituir

# Preferência: BUSCAR PELA STRING COMPLETA DO CAMINHO DA CATEGORIA
# Ex.: "SEGURANÇA ELETRÔNICA > CENTRAL DE ALARME > INSTALAÇÃO"
CATEGORY_FULLNAME = "SEGURANÇA ELETRÔNICA > CENTRAL DE ALARME > INSTALAÇÃO"

# Fallback: se quiser usar o ID numérico da categoria, defina CATEGORY_ID (ou deixe None)
CATEGORY_ID = None  # por exemplo: 29 (ou None se for usar CATEGORY_FULLNAME)

# Arquivo de saída (compatível com Linux). Vai para ~/Downloads por padrão
OUTFILE = os.path.expanduser("~/Downloads/tickets_fechados_instalacao_cameras.json")

# Paginação
PAGE_SIZE = 100

# Campos forcados no search/Ticket (mapas internos do GLPI)
FORCEDISPLAY = [2, 1, 7, 15, 12]

# === FIM CONFIG ===

session = requests.Session()
session.headers.update({
    # Content-Type não é estritamente necessário para GET, mas mantive
    "Content-Type": "application/json",
    "App-Token": APP_TOKEN,
    "Authorization": f"user_token {USER_TOKEN}"
})

def init_session():
    print("[1/6] Iniciando sessão na API do GLPI...")
    r = session.get(f"{GLPI_API_URL}/initSession")
    r.raise_for_status()
    token = r.json().get("session_token")
    print(f"[✔] Sessão iniciada. session_token: {token}")
    return token

def kill_session(token):
    try:
        session.get(f"{GLPI_API_URL}/killSession", params={"session_token": token})
        print("[✔] Sessão encerrada.")
    except Exception as e:
        print("[!] Erro ao encerrar sessão (ignorado):", e)

def search_ticket_page(token, start, end):
    """
    Faz search/Ticket para intervalo items=start-end (Range header).
    Retorna o JSON e headers.
    """
    url = f"{GLPI_API_URL}/search/Ticket"

    params = {"session_token": token}

    # Critério 0 = categoria (por nome completo ou por ID)
    if CATEGORY_FULLNAME:
        params["criteria[0][field]"] = 7           # 7 = category completename (usado também no forcedisplay)
        params["criteria[0][searchtype]"] = "contains"
        params["criteria[0][value]"] = CATEGORY_FULLNAME
    elif CATEGORY_ID is not None:
        params["criteria[0][field]"] = 6           # 6 = itilcategories_id (id numérico)
        params["criteria[0][searchtype]"] = "equals"
        params["criteria[0][value]"] = CATEGORY_ID
    else:
        raise RuntimeError("Nenhuma categoria configurada. Defina CATEGORY_FULLNAME ou CATEGORY_ID.")

    # Critério 1 = status = 6 (Fechado)
    params["criteria[1][link]"] = "AND"
    params["criteria[1][field]"] = 12              # 12 = status
    params["criteria[1][searchtype]"] = "equals"
    params["criteria[1][value]"] = 6               # 6 = fechado

    # forcedisplay
    for i, v in enumerate(FORCEDISPLAY):
        params[f"forcedisplay[{i}]"] = v

    headers = {"Range": f"items={start}-{end}"}
    print(f"[2] Requisição search/Ticket (itens {start}-{end}) -> {url}  headers={headers} params_preview={{'criteria[0]': params.get('criteria[0][value]'), 'criteria[1]': params.get('criteria[1][value]')}}")
    r = session.get(url, params=params, headers=headers, timeout=30)
    print(f"[3] HTTP {r.status_code} (content-range: {r.headers.get('Content-Range') or r.headers.get('content-range')})")
    r.raise_for_status()
    return r.json(), r.headers

def get_ticket_details(token, ticket_id):
    """GET /Ticket/<id> para pegar objeto completo do ticket."""
    url = f"{GLPI_API_URL}/Ticket/{ticket_id}"
    print(f"  [3] GET Ticket/{ticket_id} ...", end=" ")
    r = session.get(url, params={"session_token": token}, timeout=20)
    print(f"HTTP {r.status_code}")
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            print("    [!] Erro ao parsear JSON do ticket", ticket_id)
            return None
    else:
        print("[!] Falha ao obter ticket", ticket_id, "status:", r.status_code)
        return None

def extract_ids_from_search_row(row):
    """
    A partir da linha retornada pelo /search/Ticket (um dict com chaves como '2','1','7'...),
    tentamos obter o ID do ticket.
    """
    if not isinstance(row, dict):
        return None

    # prioridade para chave '2' (id) quando presente
    if "2" in row and row["2"] not in (None, ""):
        try:
            return int(row["2"])
        except:
            pass

    # fallback: procurar o primeiro valor inteiro plausível
    for k, v in row.items():
        try:
            if isinstance(v, (int,)) or (isinstance(v, str) and v.isdigit()):
                return int(v)
        except Exception:
            continue

    return None

def main():
    token = init_session()
    all_ticket_ids = []

    try:
        start = 0
        end = start + PAGE_SIZE - 1
        print(f"[4] Iniciando paginação para coletar IDs de tickets (categoria='{CATEGORY_FULLNAME or CATEGORY_ID}', status=6)")

        while True:
            payload, headers = search_ticket_page(token, start, end)
            totalcount = payload.get("totalcount", None)
            count = payload.get("count", 0)
            print(f"    -> página retornou count={count}, totalcount={totalcount}")
            rows = payload.get("data", [])

            page_ids = []
            for row in rows:
                tid = extract_ids_from_search_row(row)
                if tid:
                    page_ids.append(tid)

            print(f"    -> ids extraídos nesta página: {page_ids}")
            all_ticket_ids.extend(page_ids)

            if totalcount is not None:
                if len(all_ticket_ids) >= totalcount:
                    print("[4] Coletados todos os IDs (segundo totalcount).")
                    break

            if count == 0 or len(rows) == 0:
                print("[4] Página vazia — fim da paginação.")
                break

            start = end + 1
            end = start + PAGE_SIZE - 1

            if start > 20000:
                print("[!] Limite de paginação atingido, saindo.")
                break

            time.sleep(0.2)

        all_ticket_ids = sorted(set(all_ticket_ids))
        print(f"[5] Total de IDs coletados: {len(all_ticket_ids)}")

        detailed = []
        for i, tid in enumerate(all_ticket_ids, start=1):
            print(f"[5] ({i}/{len(all_ticket_ids)}) Buscando detalhes do ticket {tid}")
            tdata = get_ticket_details(token, tid)
            if tdata:
                obj = tdata.get("data") if isinstance(tdata, dict) and "data" in tdata else tdata
                payload = {
                    "id": obj.get("id") or obj.get("ID") or tid,
                    "name": obj.get("name"),
                    "content": obj.get("content"),
                    "entities_id": obj.get("entities_id"),
                    "itilcategories_id": obj.get("itilcategories_id"),
                    "category_completename": obj.get("itilcategories_id") and obj.get("itilcategories_id"), # mantido para referência
                    "status": obj.get("status"),
                    "date": obj.get("date"),
                    "closedate": obj.get("closedate"),
                    "solvedate": obj.get("solvedate"),
                    "users_id_recipient": obj.get("users_id_recipient"),
                    "users_id_lastupdater": obj.get("users_id_lastupdater"),
                    "_raw": obj
                }
                detailed.append(payload)
            else:
                print(f"    [!] Ignorando ticket {tid} por erro na obtenção.")
            time.sleep(0.05)

        out_dir = Path(OUTFILE).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[6] Gravando arquivo JSON em: {OUTFILE} (registros: {len(detailed)})")
        with open(OUTFILE, "w", encoding="utf-8") as f:
            json.dump(detailed, f, ensure_ascii=False, indent=2)
        print("[✔] Export concluída com sucesso!")

    except Exception as e:
        print("[!] Erro durante execução:", e)
    finally:
        kill_session(token)

if __name__ == "__main__":
    main()
