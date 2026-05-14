import json
from datetime import datetime
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from CodigoPython.bancos import conectar_postgres, pegar_mongodb, pegar_redis
from CodigoPython.modelos import (
    DadosCliente,
    AtualizarCliente,
    DadosProduto,
    AtualizarProduto,
    DadosPedido,
    AtualizarPedido,
)

app = FastAPI(title="Loja de Cosméticos da Nati - Polyglot Persistence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

banco_mongo = pegar_mongodb()
colecao_produtos = banco_mongo["produtos"]
cache_redis = pegar_redis()


def arrumar_id_mongo(produto):
    produto["id"] = str(produto["_id"])
    del produto["_id"]
    return produto


def criar_tabelas():
    conexao = conectar_postgres()
    comando = conexao.cursor()

    comando.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente SERIAL PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            email VARCHAR(160) UNIQUE NOT NULL,
            telefone VARCHAR(30),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    comando.execute(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id_pedido SERIAL PRIMARY KEY,
            id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE CASCADE,
            id_produto VARCHAR(40) NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            valor_total NUMERIC(10, 2) NOT NULL,
            status VARCHAR(30) DEFAULT 'criado',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conexao.commit()
    comando.close()
    conexao.close()


@app.on_event("startup")
def ligar_sistema():
    criar_tabelas()
    colecao_produtos.create_index("nome")
    colecao_produtos.create_index("categoria")


@app.get("/")
def abrir_telinha():
    return FileResponse("TelinhaDaLoja/index.html")


@app.get("/health")
def testar_api():
    return {"status": "ok", "mensagem": "API da lojinha de cosmeticos funcionando"}


# ------------------------- CLIENTES - POSTGRESQL -------------------------
@app.post("/clientes")
def cadastrar_cliente(dados_cliente: DadosCliente):
    conexao = conectar_postgres()
    comando = conexao.cursor()
    try:
        comando.execute(
            "INSERT INTO clientes (nome, email, telefone) VALUES (%s, %s, %s) RETURNING *",
            (dados_cliente.nome, dados_cliente.email, dados_cliente.telefone),
        )
        cliente_cadastrado = comando.fetchone()
        conexao.commit()
        return cliente_cadastrado
    except Exception as erro:
        conexao.rollback()
        raise HTTPException(status_code=400, detail=f"Deu ruim ao cadastrar cliente: {erro}")
    finally:
        comando.close()
        conexao.close()


@app.get("/clientes")
def ver_clientes():
    conexao = conectar_postgres()
    comando = conexao.cursor()
    comando.execute("SELECT * FROM clientes ORDER BY id_cliente")
    lista_clientes = comando.fetchall()
    comando.close()
    conexao.close()
    return lista_clientes


@app.get("/clientes/{id_cliente}")
def procurar_cliente(id_cliente: int):
    conexao = conectar_postgres()
    comando = conexao.cursor()
    comando.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
    cliente_achado = comando.fetchone()
    comando.close()
    conexao.close()
    if not cliente_achado:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return cliente_achado


@app.put("/clientes/{id_cliente}")
def editar_cliente(id_cliente: int, dados_novos: AtualizarCliente):
    cliente_atual = procurar_cliente(id_cliente)
    nome = dados_novos.nome if dados_novos.nome is not None else cliente_atual["nome"]
    email = dados_novos.email if dados_novos.email is not None else cliente_atual["email"]
    telefone = dados_novos.telefone if dados_novos.telefone is not None else cliente_atual["telefone"]

    conexao = conectar_postgres()
    comando = conexao.cursor()
    try:
        comando.execute(
            "UPDATE clientes SET nome=%s, email=%s, telefone=%s WHERE id_cliente=%s RETURNING *",
            (nome, email, telefone, id_cliente),
        )
        cliente_editado = comando.fetchone()
        conexao.commit()
        return cliente_editado
    except Exception as erro:
        conexao.rollback()
        raise HTTPException(status_code=400, detail=f"Deu ruim ao editar cliente: {erro}")
    finally:
        comando.close()
        conexao.close()


@app.delete("/clientes/{id_cliente}")
def apagar_cliente(id_cliente: int):
    conexao = conectar_postgres()
    comando = conexao.cursor()
    comando.execute("DELETE FROM clientes WHERE id_cliente=%s RETURNING id_cliente", (id_cliente,))
    cliente_apagado = comando.fetchone()
    conexao.commit()
    comando.close()
    conexao.close()
    if not cliente_apagado:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return {"mensagem": "Cliente apagado certinho"}


# ------------------------- PRODUTOS - MONGODB + REDIS -------------------------
@app.post("/produtos")
def cadastrar_produto(dados_produto: DadosProduto):
    produto_novo = dados_produto.model_dump()
    produto_novo["criado_em"] = datetime.now().isoformat()
    resultado = colecao_produtos.insert_one(produto_novo)
    cache_redis.delete("produtos:todos")
    return {"id": str(resultado.inserted_id), **produto_novo}


@app.get("/produtos")
def ver_produtos():
    produtos_no_cache = cache_redis.get("produtos:todos")
    if produtos_no_cache:
        return {"veio_de": "redis_cache", "dados": json.loads(produtos_no_cache)}

    lista_produtos = [arrumar_id_mongo(produto) for produto in colecao_produtos.find().sort("nome", 1)]
    cache_redis.setex("produtos:todos", 60, json.dumps(lista_produtos, default=str))
    return {"veio_de": "mongodb", "dados": lista_produtos}


@app.get("/produtos/{id_produto}")
def procurar_produto(id_produto: str):
    chave_cache = f"produto:{id_produto}"
    produto_no_cache = cache_redis.get(chave_cache)
    if produto_no_cache:
        return {"veio_de": "redis_cache", "dados": json.loads(produto_no_cache)}

    if not ObjectId.is_valid(id_produto):
        raise HTTPException(status_code=400, detail="ID de produto invalido")

    produto_achado = colecao_produtos.find_one({"_id": ObjectId(id_produto)})
    if not produto_achado:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    produto_achado = arrumar_id_mongo(produto_achado)
    cache_redis.setex(chave_cache, 60, json.dumps(produto_achado, default=str))
    return {"veio_de": "mongodb", "dados": produto_achado}


@app.put("/produtos/{id_produto}")
def editar_produto(id_produto: str, dados_novos: AtualizarProduto):
    if not ObjectId.is_valid(id_produto):
        raise HTTPException(status_code=400, detail="ID de produto invalido")

    campos_para_trocar = {chave: valor for chave, valor in dados_novos.model_dump().items() if valor is not None}
    if not campos_para_trocar:
        raise HTTPException(status_code=400, detail="Nenhum dado enviado para atualizar")

    resultado = colecao_produtos.update_one({"_id": ObjectId(id_produto)}, {"$set": campos_para_trocar})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    cache_redis.delete("produtos:todos")
    cache_redis.delete(f"produto:{id_produto}")
    return procurar_produto(id_produto)


@app.delete("/produtos/{id_produto}")
def apagar_produto(id_produto: str):
    if not ObjectId.is_valid(id_produto):
        raise HTTPException(status_code=400, detail="ID de produto invalido")

    resultado = colecao_produtos.delete_one({"_id": ObjectId(id_produto)})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    cache_redis.delete("produtos:todos")
    cache_redis.delete(f"produto:{id_produto}")
    return {"mensagem": "Produto apagado certinho"}


# ------------------------- PEDIDOS - POSTGRESQL + MONGODB -------------------------
@app.post("/pedidos")
def cadastrar_pedido(dados_pedido: DadosPedido):
    procurar_cliente(dados_pedido.id_cliente)

    if not ObjectId.is_valid(dados_pedido.id_produto):
        raise HTTPException(status_code=400, detail="ID de produto invalido")

    produto_escolhido = colecao_produtos.find_one({"_id": ObjectId(dados_pedido.id_produto)})
    if not produto_escolhido:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    if produto_escolhido["estoque"] < dados_pedido.quantidade:
        raise HTTPException(status_code=400, detail="Estoque insuficiente")

    valor_total = float(produto_escolhido["preco"]) * dados_pedido.quantidade

    conexao = conectar_postgres()
    comando = conexao.cursor()
    try:
        comando.execute(
            """
            INSERT INTO pedidos (id_cliente, id_produto, quantidade, valor_total)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (dados_pedido.id_cliente, dados_pedido.id_produto, dados_pedido.quantidade, valor_total),
        )
        pedido_cadastrado = comando.fetchone()
        conexao.commit()

        colecao_produtos.update_one(
            {"_id": ObjectId(dados_pedido.id_produto)},
            {"$inc": {"estoque": -dados_pedido.quantidade}},
        )
        cache_redis.delete("produtos:todos")
        cache_redis.delete(f"produto:{dados_pedido.id_produto}")

        return pedido_cadastrado
    except Exception as erro:
        conexao.rollback()
        raise HTTPException(status_code=400, detail=f"Deu ruim ao cadastrar pedido: {erro}")
    finally:
        comando.close()
        conexao.close()


@app.get("/pedidos")
def ver_pedidos():
    conexao = conectar_postgres()
    comando = conexao.cursor()
    comando.execute(
        """
        SELECT p.*, c.nome AS nome_cliente, c.email AS email_cliente
        FROM pedidos p
        JOIN clientes c ON c.id_cliente = p.id_cliente
        ORDER BY p.id_pedido
        """
    )
    lista_pedidos = comando.fetchall()
    comando.close()
    conexao.close()
    return lista_pedidos


@app.put("/pedidos/{id_pedido}")
def editar_status_pedido(id_pedido: int, dados_novos: AtualizarPedido):
    conexao = conectar_postgres()
    comando = conexao.cursor()
    comando.execute(
        "UPDATE pedidos SET status=%s WHERE id_pedido=%s RETURNING *",
        (dados_novos.status, id_pedido),
    )
    pedido_editado = comando.fetchone()
    conexao.commit()
    comando.close()
    conexao.close()
    if not pedido_editado:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return pedido_editado


@app.delete("/pedidos/{id_pedido}")
def apagar_pedido(id_pedido: int):
    conexao = conectar_postgres()
    comando = conexao.cursor()
    comando.execute("DELETE FROM pedidos WHERE id_pedido=%s RETURNING id_pedido", (id_pedido,))
    pedido_apagado = comando.fetchone()
    conexao.commit()
    comando.close()
    conexao.close()
    if not pedido_apagado:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return {"mensagem": "Pedido apagado certinho"}
