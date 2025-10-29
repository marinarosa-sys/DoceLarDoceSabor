from flask import Flask, render_template, request, redirect, session, url_for
from sqlalchemy import text
from bk_usuario import db, Usuario  # Import do models
import os
from bk_usuario import db, Usuario  # Import do models
from bk_receita import Receita
from sqlalchemy import func
from bk_receita import Ingrediente
from bk_receita import IngredienteReceita

from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join("static", "imagens_receitas")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

        

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Configuração do SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@127.0.0.1:3306/db_culinaria"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializa o db com o app (IMPORTANTE: deve ser feito aqui)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)


# 🏠 Rota inicial
@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("explorar"))
    else:
        return render_template("index.html")

# Rota Login
@app.route("/login", methods=["POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        senha = request.form['senha']

        user = Usuario.query.filter_by(username=username).first()

        if user and user.check_password(senha):
            if user.status != 'ativo':
                return render_template("login.html", error="Esta conta foi deletada.")
            session['username'] = user.username
            return redirect(url_for('explorar'))
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
            return redirect(url_for('explorar'))

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

# Rota Explorar
@app.route("/explorar")
def explorar():

    if "username" not in session:
        return redirect(url_for("home"))

    termo = request.args.get("q", "").strip()
    print(f"🔍 Termo de busca recebido: '{termo}'")

    if termo:
        receitas = (
            Receita.query
            .filter(func.lower(Receita.titulo).like(f"%{termo.lower()}%"))
            .all()
        )
    else:
        receitas = Receita.query.all()

    return render_template("explorar.html", receitas=receitas)


@app.route("/nova_receita", methods=["GET", "POST"])
def nova_receita():
    if request.method == "POST":
        titulo = request.form["titulo"]
        
        file = request.files.get("imagem")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            imagem_path = f"imagens_receitas/{filename}"  # caminho relativo para usar no HTML
        else:
            imagem_path = None

        instrucoes = request.form["instrucoes"]
        categoria = request.form["categoria"]
        utensilios = request.form["utensilios"]

        # Cria a receita
        nova = Receita(
            titulo=titulo,
            imagem=imagem_path,
            instrucoes=instrucoes,
            categoria=categoria,
            utensilios=utensilios
        )
        db.session.add(nova)
        db.session.commit()

        # Pega os ingredientes enviados pelo formulário
        nomes_ingredientes = request.form.getlist("nome_ingrediente[]")
        quantidades = request.form.getlist("quantidade_ingrediente[]")
        unidades = request.form.getlist("unidade_medida[]")

        for nome, qtd, unidade in zip(nomes_ingredientes, quantidades, unidades):
            if nome.strip():  # só adiciona se o campo não estiver vazio
                # Verifica se o ingrediente já existe
                ingrediente_existente = Ingrediente.query.filter_by(nome_ingrediente=nome).first()

                if not ingrediente_existente:
                    ingrediente = Ingrediente(nome_ingrediente=nome, unidade_medida=unidade)
                    db.session.add(ingrediente)
                    db.session.commit()
                else:
                    ingrediente = ingrediente_existente

                # Relaciona com a receita
                relacao = IngredienteReceita(
                    fk_receita=nova.id,
                    fk_ingrediente=ingrediente.id_ingrediente,
                    quantidade_ingrediente_receita=qtd
                )
                db.session.add(relacao)

        db.session.commit()
        return redirect(url_for("explorar"))

    return render_template("nova_receita.html")



# Rota Detalhes
@app.route("/receita/<int:id>")
def detalhe_receita(id):
    receita = Receita.query.get_or_404(id)
    return render_template("receita.html", receita=receita)




# Inicialização do servidor
if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
            db.session.execute(text("SELECT 1"))
            print("✅ Conectado ao MySQL e tabelas criadas/verificadas com sucesso!")

            # ✅ Popula o banco apenas se estiver vazio
            if Receita.query.count() == 0:
                popular_receitas()

        except Exception as e:
            print("❌ Erro ao conectar ou criar tabelas:", e)
    app.run(debug=True)

