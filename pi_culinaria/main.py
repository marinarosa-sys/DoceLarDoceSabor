from flask import Flask, render_template, request, redirect, session, url_for
from sqlalchemy import text
from bk_usuario import db, Usuario  # Import do models
import os
from bk_usuario import db, Usuario  # Import do models
from bk_receita import Receita, listar_receitas_usuario, Avaliacao
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
@app.route("/login", methods=["POST", "GET"])
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
    return Usuario.cadastro_usuario()


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

# ✏️ Editar conta# ✏️ Editar conta
@app.route("/editar_conta", methods=["GET", "POST"])
def editar_conta():
    return Usuario.editar_conta_usuario()

@app.route("/desativar_conta", methods=["POST"])
def desativar_conta():
    return Usuario.desativar_conta_usuario()


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

@app.route("/avaliar_receita/<int:id>", methods=["POST"])
def avaliar_receita(id):
    if "username" not in session:
        return redirect(url_for("login"))

    user = Usuario.query.filter_by(username=session["username"]).first()
    receita = Receita.query.get_or_404(id)

    # 🔒 Bloqueia se o usuário for o autor
    if receita.fk_usuario == user.id_usuario:
        return redirect(url_for("detalhe_receita", id=id))

    nota = int(request.form["nota"])
    comentario = request.form.get("comentario", "")

    Avaliacao.salvar_avaliacao(user.id_usuario, id, nota, comentario)
    return redirect(url_for("detalhe_receita", id=id))



@app.route("/nova_receita", methods=["GET", "POST"])
def nova_receita():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        titulo = request.form["titulo"]

        file = request.files.get("imagem")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            imagem_path = f"imagens_receitas/{filename}"
        else:
            imagem_path = None

        instrucoes = request.form["instrucoes"]
        categoria = request.form["categoria"]
        utensilios = request.form["utensilios"]

        # 🔍 Pega o usuário logado
        user = Usuario.query.filter_by(username=session["username"]).first()

        # Cria a receita vinculada ao usuário
        nova = Receita(
            titulo=titulo,
            imagem=imagem_path,
            instrucoes=instrucoes,
            categoria=categoria,
            utensilios=utensilios,
            fk_usuario=user.id_usuario  # 👈 salva o ID do usuário
        )
        db.session.add(nova)
        db.session.commit()

        # Pega os ingredientes enviados pelo formulário
        nomes_ingredientes = request.form.getlist("nome_ingrediente[]")
        quantidades = request.form.getlist("quantidade_ingrediente[]")
        unidades = request.form.getlist("unidade_medida[]")

        for nome, qtd, unidade in zip(nomes_ingredientes, quantidades, unidades):
            if nome.strip():
                ingrediente_existente = Ingrediente.query.filter_by(nome_ingrediente=nome).first()

                if not ingrediente_existente:
                    ingrediente = Ingrediente(nome_ingrediente=nome, unidade_medida=unidade)
                    db.session.add(ingrediente)
                    db.session.commit()
                else:
                    ingrediente = ingrediente_existente

                relacao = IngredienteReceita(
                    fk_receita=nova.id,
                    fk_ingrediente=ingrediente.id_ingrediente,
                    quantidade_ingrediente_receita=qtd
                )
                db.session.add(relacao)

        db.session.commit()
        return redirect(url_for("explorar"))

    return render_template("nova_receita.html")




@app.route("/minhas_receitas")
def minhas_receitas():
    if "username" not in session:
        return redirect(url_for("login"))

    user = Usuario.query.filter_by(username=session["username"]).first()
    receitas = listar_receitas_usuario(user.id_usuario)

    return render_template("minhas_receitas.html", receitas=receitas)


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


        except Exception as e:
            print("❌ Erro ao conectar ou criar tabelas:", e)
    app.run(debug=True)

