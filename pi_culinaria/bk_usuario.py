from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, url_for

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
        from werkzeug.security import check_password_hash
        return check_password_hash(self.senha, senha)

    def login_usuario():
        if request.method == "POST":
            username = request.form['username']
            senha = request.form['senha']

            user = Usuario.query.filter_by(username=username).first()

            if user and user.check_password(senha):
                if user.status != 'ativo':
                    return render_template("login.html", error="Esta conta está desativada.")
                session['username'] = user.username
                return redirect(url_for('dashboard'))
            else:
                return render_template("login.html", error="Usuário ou senha inválidos")
            
        return render_template("login.html")
    
    def cadastro_usuario():
        if request.method == "POST":
            nome_completo = request.form['nome_completo']
            username = request.form['username']
            email = request.form['email_usuario']
            senha = request.form['senha']

            user = Usuario.query.filter_by(email_usuario=email).first()

            if user:
                return render_template("cadastro.html", error="E-mail já cadastrado")
            else:
                novo_usuario = Usuario(
                    nome_completo=nome_completo,
                    username=username,
                    email_usuario=email
                )
                novo_usuario.set_password(senha)
                db.session.add(novo_usuario)
                db.session.commit()

                session['username'] = username
                return redirect(url_for('dashboard'))

        return render_template("cadastro.html")
    
    def editar_conta_usuario():
        if "username" not in session:
            return redirect(url_for("login"))

        user = Usuario.query.filter_by(username=session["username"]).first()

        if request.method == "POST":
            novo_nome = request.form["nome_completo"]
            novo_email = request.form["email_usuario"]
            novo_username = request.form["username"]
            nova_senha = request.form["senha"]

            # Atualiza os campos
            user.nome_completo = novo_nome
            user.email_usuario = novo_email
            user.username = novo_username

            # Atualiza a senha apenas se o campo não estiver vazio
            if nova_senha.strip():
                user.set_password(nova_senha)

            try:
                db.session.commit()
                # Atualiza sessão se mudar o nome de usuário
                session["username"] = novo_username
                return render_template("editar_conta.html", user=user, sucesso="Dados atualizados com sucesso!")
            except Exception as e:
                db.session.rollback()
                erro_msg = "Erro ao atualizar dados (possível e-mail ou username já em uso)."
                print("Erro:", e)
                return render_template("editar_conta.html", user=user, erro=erro_msg)

        return render_template("editar_conta.html", user=user)
    
    def desativar_conta_usuario():
        if "username" not in session:
            return redirect(url_for("login"))
        
        user = Usuario.query.filter_by(username=session["username"]).first()
        if not user:
            return redirect(url_for("dashboard"))
        
        senha_digitada = request.form.get("senha_confirm")

        if not user.check_password(senha_digitada):
            return render_template("editar_conta.html", user=user, erro="Senha incorreta. Não foi possível desativar a conta.")
        
        user.status = "inativo"
        db.session.commit()
        session.pop("username", None)
        return render_template("index.html", sucesso="Sua conta foi desativada.")   
class Favorito(db.Model):
    __tablename__ = "tb_favoritos"

    id_favorito = db.Column(db.Integer, primary_key=True)
    fk_usuario = db.Column(db.Integer, db.ForeignKey("tb_usuarios.id_usuario"), nullable=False)
    fk_receita = db.Column(db.Integer, db.ForeignKey("tb_receitas.id"), nullable=False)

class Intolerancia(db.Model):
    __tablename__ = "tb_intolerancias"

    id_intolerancia = db.Column(db.Integer, primary_key=True)
    fk_usuario = db.Column(db.Integer, db.ForeignKey("tb_usuarios.id_usuario"), nullable=False)
    fk_ingrediente = db.Column(db.Integer, db.ForeignKey("tb_ingredientes.id_ingrediente"), nullable=False)

    
    
