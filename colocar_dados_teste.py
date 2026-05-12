from CodigoPython.bancos import conectar_postgres, pegar_mongodb, pegar_redis


def cadastrar_clientes_teste():
    conexao = conectar_postgres()
    comando = conexao.cursor()

    comando.execute(
        """
        INSERT INTO clientes (nome, email, telefone)
        VALUES
            ('Natasha Almeida', 'natasha@email.com', '11999990000'),
            ('Clara Silva', 'clara@email.com', '11988887777'),
            ('Eduardo Lima', 'eduardo@email.com', '11977776666')
        ON CONFLICT (email) DO NOTHING;
        """
    )

    conexao.commit()
    comando.close()
    conexao.close()


def cadastrar_produtos_teste():
    banco_mongo = pegar_mongodb()
    produtos = banco_mongo["produtos"]

    if produtos.count_documents({}) > 0:
        return

    produtos.insert_many(
        [
            {
                "nome": "Serum Facial Vitamina C",
                "marca": "Glow Beauty",
                "categoria": "Skincare",
                "preco": 89.90,
                "estoque": 30,
                "descricao": "Serum antioxidante para iluminar a pele.",
                "ingredientes": ["vitamina C", "acido hialuronico"],
                "tipo_pele": "todos os tipos",
            },
            {
                "nome": "Hidratante Facial Oil Free",
                "marca": "Bella Skin",
                "categoria": "Skincare",
                "preco": 59.90,
                "estoque": 45,
                "descricao": "Hidratante leve para pele oleosa e mista.",
                "ingredientes": ["niacinamida", "pantenol"],
                "tipo_pele": "oleosa",
            },
            {
                "nome": "Batom Matte Nude Rosado",
                "marca": "Lumiere Make",
                "categoria": "Maquiagem",
                "preco": 34.90,
                "estoque": 60,
                "descricao": "Batom matte confortavel para o dia a dia.",
                "ingredientes": ["manteiga de karite", "vitamina E"],
                "tipo_pele": None,
            },
        ]
    )


def limpar_cache_antigo():
    cache_redis = pegar_redis()
    cache_redis.flushdb()


if __name__ == "__main__":
    cadastrar_clientes_teste()
    cadastrar_produtos_teste()
    limpar_cache_antigo()
    print("Dados de teste colocados com sucesso :) ")
