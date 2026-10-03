import json
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

PARCEIRO_ID = "33337"
URL_BASE = "https://www.ybera.com"
URL_MAIS_VENDIDOS = "https://www.ybera.com/mais-vendidos"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

PALAVRAS_IGNORADAS = [
    "todos os produtos",
    "produtos",
    "menu",
    "carrinho",
    "minha conta",
    "voltar",
    "mostrar mais",
    "avise-me",
    "politica",
    "termos",
]


def aplicar_link_afiliado(url_produto, id_afiliado):
    if not url_produto.startswith("http"):
        url_produto = urllib.parse.urljoin(URL_BASE, url_produto)
    parsed = urllib.parse.urlparse(url_produto)
    qs = urllib.parse.parse_qs(parsed.query)
    qs["parceiro"] = [id_afiliado]
    novo_query = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            novo_query,
            parsed.fragment,
        )
    )


def extrair_mais_vendidos():
    print(f"[*] Buscando os mais vendidos em: {URL_MAIS_VENDIDOS}")
    resp = requests.get(URL_MAIS_VENDIDOS, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        print(f"[!] Erro ao acessar: Status {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    produtos = []
    links_vistos = set()

    for item in soup.find_all("a", href=True):
        href = item["href"]

        # Filtra apenas links para produtos reais
        if not (
            "/p/" in href
            or "/produto/" in href
            or "/kit-" in href
            or "-ybera" in href
            or "fashion-gold" in href
            or "terra-coco" in href
            or "oleo-de-mirra" in href
        ):
            continue

        container = item.find_parent(
            ["article", "li", "div", "form"]
        ) or item.find_next_sibling(["div", "article"])
        if not container:
            container = item

        # Imagem
        img_elem = container.find("img") or item.find("img")
        if not img_elem:
            continue

        imagem = (
            img_elem.get("data-src")
            or img_elem.get("src")
            or img_elem.get("srcset", "").split()[0]
        )
        if (
            not imagem
            or "logo" in imagem.lower()
            or "icon" in imagem.lower()
            or "banner" in imagem.lower()
        ):
            continue
        if imagem.startswith("//"):
            imagem = "https:" + imagem

        # Título
        nome_elem = (
            container.select_one(
                "h1, h2, h3, h4, .product-title, .title, [class*='name']"
            )
            or img_elem.get("alt")
            or item
        )
        nome = (
            nome_elem.get_text(strip=True)
            if hasattr(nome_elem, "get_text")
            else str(nome_elem)
        )

        nome_limpo = nome.strip().lower()
        if (
            len(nome_limpo) < 8
            or any(palavra in nome_limpo for palavra in PALAVRAS_IGNORADAS)
            or "adicionar" in nome_limpo
        ):
            continue

        url_final = aplicar_link_afiliado(href, PARCEIRO_ID)
        if url_final in links_vistos:
            continue
        links_vistos.add(url_final)

        # Captura de preços
        texto_todo = container.get_text(separator=" ")
        precos = re.findall(r"R\$\s*[\d\.,]+", texto_todo)

        preco_antigo = ""
        preco_atual = "Consulte Oferta"
        if len(precos) >= 2:
            preco_antigo = precos[0]
            preco_atual = precos[1]
        elif len(precos) == 1:
            preco_atual = precos[0]

        # Selos de destaque dinâmicos
        posicao = len(produtos) + 1
        if posicao == 1:
            tag = "⭐ Mais Vendido"
        elif posicao == 2:
            tag = "🔥 Top Procurado"
        elif preco_antigo:
            tag = "💥 Em Promoção"
        else:
            tag = "✨ Destaque"

        produtos.append(
            {
                "nome": nome[:80],
                "precoAntigo": preco_antigo,
                "precoAtual": preco_atual,
                "imagem": imagem,
                "link": url_final,
                "tag": tag,
            }
        )

        if len(produtos) >= 12:
            break

    print(f"[✓] {len(produtos)} produtos mais vendidos processados!")
    return produtos


if __name__ == "__main__":
    lista = extrair_mais_vendidos()
    with open("produtos.json", "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
