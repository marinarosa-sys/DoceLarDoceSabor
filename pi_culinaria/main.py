# app.py
from flask import Flask, render_template, request, redirect, session, url_for
from sqlalchemy import text
from bk_usuario import db, Usuario  # Import do models

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Configuração do SQL Alchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@127.0.0.1:3306/db_culinaria"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializa o db com o app (IMPORTANTE: deve ser feito aqui)
db.init_app(app)

# Rota Home
@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html")

# Rota Login
@app.route("/login", methods=["POST"])
def login():
    username = request.form['username']
    senha = request.form['senha']
    
    # Usar o contexto da aplicação para a query
    with app.app_context():
        user = Usuario.query.filter_by(username=username).first()

        # Prints de debug no terminal
        print(f"DEBUG: Usuário digitado: {username}")
        print(f"DEBUG: Usuário encontrado no banco: {user}")
        if user:
            print(f"DEBUG: Hash armazenado: {user.senha}")
            print(f"DEBUG: Senha confere? {user.check_password(senha)}")

        if user and user.check_password(senha):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template("index.html", error="Usuário ou senha inválidos")

# Rota Cadastro
@app.route("/cadastro", methods=["POST"])
def cadastro():
    username = request.form['username']
    senha = request.form['senha']
    
    with app.app_context():
        user = Usuario.query.filter_by(username=username).first()

        if user:
            return render_template("index.html", error="Usuário já cadastrado")
        else:
            new_user = Usuario(username=username)
            new_user.set_password(senha)
            db.session.add(new_user)
            db.session.commit()
            session['username'] = username
            return redirect(url_for('dashboard'))

# Rota Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html", username=session['username'])
    return redirect(url_for('home'))

# Rota Logout
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for("home"))

# Inicialização do servidor
if __name__ == "__main__":
    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
            print("✅ Conectado ao MySQL com sucesso!")
        except Exception as e:
            print("❌ Erro ao conectar:", e)
        app.run(debug=True)