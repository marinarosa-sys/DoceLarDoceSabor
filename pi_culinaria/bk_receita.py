# bk_receita.py
from flask_sqlalchemy import SQLAlchemy
from bk_usuario import db  # reutiliza a mesma instância do SQLAlchemy

class Receita(db.Model):
    __tablename__ = "tb_receitas"

    id = db.Column(db.Integer, primary_key=True)
    fk_usuario = db.Column(db.Integer, db.ForeignKey("tb_usuarios.id_usuario"), nullable=False)
    titulo = db.Column(db.String(255), nullable=False)
    imagem = db.Column(db.String(500))
    instrucoes = db.Column(db.Text)
    categoria = db.Column(db.String(100))
    utensilios = db.Column(db.Text)

    # 🆕 Novos campos
    dificuldade = db.Column(db.String(50))  # Ex: Fácil, Médio, Difícil
    tempo_preparo = db.Column(db.String(50))  # Ex: "45 minutos", "1h 30min"
    custo = db.Column(db.String(50))  # Ex: "Baixo", "Médio", "Alto"
    porcoes = db.Column(db.Integer)  # Ex: número de pessoas ou porções

    # Relacionamento com o usuário
    usuario = db.relationship("Usuario", backref="receitas", lazy=True)

    # Relacionamento com ingredientes
    ingredientes_receita = db.relationship(
        "IngredienteReceita",
        back_populates="receita",
        lazy="joined"
    )

    def apagar_receitas_usuario(id_usuario):
        # Buscar todas as receitas do usuário
        receitas = Receita.query.filter_by(fk_usuario=id_usuario).all()

        for receita in receitas:
            # Apaga avaliações relacionadas
            Avaliacao.query.filter_by(fk_receita=receita.id).delete()

            # Apaga ingredientes relacionados
            IngredienteReceita.query.filter_by(fk_receita=receita.id).delete()

            # Apaga a própria receita
            db.session.delete(receita)

        db.session.commit()



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


class Avaliacao(db.Model):
    __tablename__ = "tb_avaliacoes"

    id_avaliacao = db.Column(db.Integer, primary_key=True)
    fk_usuario = db.Column(db.Integer, db.ForeignKey("tb_usuarios.id_usuario"), nullable=False)
    fk_receita = db.Column(db.Integer, db.ForeignKey("tb_receitas.id"), nullable=False)
    nota = db.Column(db.Integer, nullable=False)  # de 1 a 5 estrelas
    comentario = db.Column(db.Text)
    data_avaliacao = db.Column(db.DateTime, server_default=db.func.now())
    treinado = db.Column(db.Boolean, default=False)

    usuario = db.relationship("Usuario", backref="avaliacoes", lazy=True)
    receita = db.relationship("Receita", backref="avaliacoes", lazy=True)

    @staticmethod
    def salvar_avaliacao(fk_usuario, fk_receita, nota, comentario=""):
        """Cria ou atualiza a avaliação de um usuário em uma receita."""
        avaliacao_existente = Avaliacao.query.filter_by(fk_usuario=fk_usuario, fk_receita=fk_receita).first()

        if avaliacao_existente:
            avaliacao_existente.nota = nota
            avaliacao_existente.comentario = comentario
        else:
            nova = Avaliacao(
                fk_usuario=fk_usuario,
                fk_receita=fk_receita,
                nota=nota,
                comentario=comentario
            )
            db.session.add(nova)

        db.session.commit()


def listar_receitas_usuario(id_usuario):
    return Receita.query.filter_by(fk_usuario=id_usuario).all()
