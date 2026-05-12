# Como abrir os bancos do projeto

## PostgreSQL

Pode abrir pelo **DBeaver** ou **pgAdmin**.

Configuração:

```text
Host: localhost
Porta: 5432
Database: loja_cosmeticos
Usuario: postgres
Senha: postgres
```

Tabelas para olhar:

```text
clientes
pedidos
```

Consultas:

```sql
SELECT * FROM clientes;
SELECT * FROM pedidos;
```

---

## MongoDB

Pode abrir pelo **MongoDB Compass**.

URL:

```text
mongodb://localhost:27017
```

Banco:

```text
loja_cosmeticos_docs
```

Coleção:

```text
produtos
```

---

## Redis

Pode abrir pelo **RedisInsight**.

Configuração:

```text
Host: localhost
Porta: 6379
Usuario: deixar vazio
Senha: deixar vazio
```

Chaves que aparecem quando os produtos são consultados:

```text
produtos:todos
produto:ID_DO_PRODUTO
```

Pelo terminal também dá para abrir assim:

```bash
docker exec -it banco_redis_loja redis-cli
```

E dentro dele:

```bash
KEYS *
GET produtos:todos
```
