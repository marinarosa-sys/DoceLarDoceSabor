# bk_receita.py
from flask_sqlalchemy import SQLAlchemy
from bk_usuario import db  # reutiliza a mesma instância do SQLAlchemy

class Receita(db.Model):
    __tablename__ = "tb_receitas"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    imagem = db.Column(db.String(500))
    instrucoes = db.Column(db.Text)
    categoria = db.Column(db.String(100))
    utensilios = db.Column(db.Text)

    # Relacionamento com ingredientes
    ingredientes_receita = db.relationship(
        "IngredienteReceita",
        back_populates="receita",
        lazy="joined"
    )

class IngredienteReceita(db.Model):
    __tablename__ = "tb_ingrediente_receita"

    id_ingrediente_receita = db.Column(db.Integer, primary_key=True)
    fk_receita = db.Column(db.Integer, db.ForeignKey("tb_receitas.id"), nullable=False)
    fk_ingrediente = db.Column(db.Integer, db.ForeignKey("tb_ingredientes.id_ingrediente"), nullable=False)
    quantidade_ingrediente_receita = db.Column(db.String(50))

    receita = db.relationship("Receita", back_populates="ingredientes_receita")
    ingrediente = db.relationship("Ingrediente")
    
class Ingrediente(db.Model):
    __tablename__ = "tb_ingredientes"

    id_ingrediente = db.Column(db.Integer, primary_key=True)
    nome_ingrediente = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(50))
