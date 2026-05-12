from typing import Optional, List
from pydantic import BaseModel, Field


class DadosCliente(BaseModel):
    nome: str
    email: str
    telefone: Optional[str] = None


class AtualizarCliente(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class DadosProduto(BaseModel):
    nome: str
    marca: str
    categoria: str
    preco: float = Field(gt=0)
    estoque: int = Field(ge=0)
    descricao: Optional[str] = None
    ingredientes: List[str] = []
    tipo_pele: Optional[str] = None


class AtualizarProduto(BaseModel):
    nome: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    preco: Optional[float] = Field(default=None, gt=0)
    estoque: Optional[int] = Field(default=None, ge=0)
    descricao: Optional[str] = None
    ingredientes: Optional[List[str]] = None
    tipo_pele: Optional[str] = None


class DadosPedido(BaseModel):
    id_cliente: int
    id_produto: str
    quantidade: int = Field(gt=0)


class AtualizarPedido(BaseModel):
    status: str
