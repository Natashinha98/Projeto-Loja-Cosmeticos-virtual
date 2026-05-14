import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
import redis
from dotenv import load_dotenv

load_dotenv()


def conectar_postgres():
    # banco relacional: guarda clientes e pedidos
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "loja_cosmeticos"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor,
    )


def pegar_mongodb():
    # banco de documentos: guarda os cosmeticos/produtos
    endereco = os.getenv("MONGO_HOST", "localhost")
    porta = os.getenv("MONGO_PORT", "27017")
    nome_banco = os.getenv("MONGO_DB", "loja_cosmeticos_docs")
    cliente_mongo = MongoClient(f"mongodb://{endereco}:{porta}/")
    return cliente_mongo[nome_banco]


def pegar_redis():
    # cache: guarda consultas rapidas de produtos
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
