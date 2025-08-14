import requests

# URL da API
# Conexão de teste para verificar se a API está acessível em glpi-manutencao.clickip.local
# session_token = nbu5tlkd6vold1ad5kv84kpfur

url = "http://glpi-manutencao.clickip.local:5071/apirest.php/initSession"

# Cabeçalhos necessários

headers = {
    "Content-Type": "application/json", # ou "application/x-www-form-urlencoded" dependendo da API
    "Authorization": "user_token 5YImkRED6xBgKX7gg5qq6n4QTIj4y1bP549ETE1i", #"user_token SEU_USER_TOKEN"
    "App-Token": "eYoExwDP3ghgK7VlM0e5XYiggsU987A97OtsC1KO"
}

# Requisição GET para iniciar a sessão

response = requests.get(url, headers=headers)

# Exibir resposta

if response.status_code == 200:
    print("Conexão com a API em glpi-manutencao OK")
    print(response.json())
else:
    print(f"Erro {response.status_code}: {response.text}")
