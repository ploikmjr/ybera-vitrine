import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import re

PARCEIRO_ID = "33337"
URL_BASE = "https://www.ybera.com"
URL_ALVO = "https://www.ybera.com/mais-vendidos"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

def aplicar_link_afiliado(url_produto, id_afiliado):
    if not url_produto.startswith("http"):
        url_produto = urllib.parse.urljoin(URL_BASE, url_produto)
    parsed = urllib.parse.urlparse(url_produto)
    qs = urllib.parse.parse_qs(parsed.query)
    qs['parceiro'] = [id_afiliado]
    novo_query = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, novo_query, parsed.fragment))

def extrair_produtos():
    print(f"[*] Acessando {URL_ALVO}...")
    resp = requests.get(URL_ALVO, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        print(f"[!] Erro ao acessar a loja: Status {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    produtos = []
    links_vistos = set()

    for item in soup.find_all('a', href=True):
        href = item['href']
        if ('/p/' in href or '/produto' in href or '/kit-' in href) and href not in links_vistos:
            container = item.find_parent(['div', 'article', 'li']) or item
            links_vistos.add(href)

            nome_elem = container.select_one("h2, h3, .product-title, .title, [class*='name']") or item
            nome = nome_elem.get_text(strip=True) if nome_elem else "Produto Ybera"

            if len(nome) < 5 or "adicionar" in nome.lower():
                continue

            img_elem = container.find('img')
            imagem = ""
            if img_elem:
                imagem = img_elem.get('data-src') or img_elem.get('src') or img_elem.get('srcset', '').split()[0]
                if imagem and imagem.startswith('//'):
                    imagem = 'https:' + imagem

            texto_todo = container.get_text(separator=' ')
            precos = re.findall(r'R\$\s*[\d\.,]+', texto_todo)

            preco_antigo = ""
            preco_atual = "Consulte Oferta"
            if len(precos) >= 2:
                preco_antigo = precos[0]
                preco_atual = precos[1]
            elif len(precos) == 1:
                preco_atual = precos[0]

            link_final = aplicar_link_afiliado(href, PARCEIRO_ID)

            produtos.append({
                "nome": nome[:75],
                "precoAntigo": preco_antigo,
                "precoAtual": preco_atual,
                "imagem": imagem or "https://images.unsplash.com/photo-1608248597359-002d2427b524?auto=format&fit=crop&w=600&q=80",
                "link": link_final,
                "tag": "Mais Vendido" if len(produtos) == 0 else "Destaque"
            })

            if len(produtos) >= 12:
                break

    return produtos

if __name__ == "__main__":
    lista = extrair_produtos()
    with open("produtos.json", "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
    print(f"[✓] {len(lista)} produtos salvos em produtos.json!")
