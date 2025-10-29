from flask import Flask, render_template, request, redirect, session, url_for
from sqlalchemy import text
from bk_usuario import db, Usuario

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Configuração do SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@127.0.0.1:3306/db_culinaria"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


# 🏠 Rota inicial
@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html")


# 🔐 Página de login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        senha = request.form['senha']

        user = Usuario.query.filter_by(username=username).first()

        if user and user.check_password(senha):
            if user.status != 'ativo':
                return render_template("login.html", error="Esta conta foi deletada.")
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="Usuário ou senha inválidos")

    return render_template("login.html")


# 📝 Página de cadastro
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
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


# 📊 Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html", username=session['username'])
    return redirect(url_for('login'))


# 🚪 Logout
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for("home"))

# ✏️ Editar conta
@app.route("/editar_conta", methods=["GET", "POST"])
def editar_conta():
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

@app.route("/desativar_conta", methods=["POST"])
def desativar_conta():
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


# 🚀 Inicialização
if __name__ == "__main__":
    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
            print("✅ Conectado ao MySQL com sucesso!")
        except Exception as e:
            print("❌ Erro ao conectar:", e)
        app.run(debug=True)
