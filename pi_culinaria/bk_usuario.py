from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "tb_usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(150), nullable=False)
    email_usuario = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('ativo','inativo', name='status_enum'), nullable=False, default='ativo')

    def set_password(self, senha):
        self.senha = generate_password_hash(senha)
    
    def check_password(self, senha):
        return check_password_hash(self.senha, senha)
    
    
