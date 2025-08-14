import requests

# URL da API
# Conexão de teste para verificar se a API está acessível em glpi-manutencao.clickip.local

#session_token = fc23lteea86lq5ms8apvvh8sic

url = "https://chamados.clickip.com.br/apirest.php/initSession"

# Cabeçalhos necessários

headers = {
    "Content-Type": "application/json", # ou "application/x-www-form-urlencoded" dependendo da API
    "Authorization": "user_token ibUwLdHtUnGKGm3vTnfN05Fg2XQ3arhwNlEMyPyI", #"user_token SEU_USER_TOKEN"
    "App-Token": "1bLyuIOpBIJrZIheMP0m9uqXgKD8rxoaxj8ruGlo"
}

# Requisição GET para iniciar a sessão

response = requests.get(url, headers=headers)

# Exibir resposta

if response.status_code == 200:
    print("Conexão com a API em glpi-ti OK")
    print(response.json())
else:
    print(f"Erro {response.status_code}: {response.text}")
