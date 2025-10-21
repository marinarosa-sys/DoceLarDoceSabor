# models.py
from flask_sqlalchemy import SQLAlchemy

# Cria uma única instância do SQLAlchemy
db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "tb_usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)

    def set_password(self, senha):
        from werkzeug.security import generate_password_hash
        self.senha = generate_password_hash(senha)
    
    def check_password(self, senha):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.senha, senha)