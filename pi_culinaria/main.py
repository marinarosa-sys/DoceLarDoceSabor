from flask import Flask, render_template, request, redirect, session, url_for
from sqlalchemy import text
from bk_usuario import db, Usuario  # Import do models
import os
from bk_usuario import db, Usuario  # Import do models
from bk_receita import Receita, listar_receitas_usuario, Avaliacao
from sqlalchemy import func
from bk_receita import Ingrediente
from bk_receita import IngredienteReceita
from bk_usuario import Favorito, Intolerancia

from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join("static", "imagens_receitas")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

        

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

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
    session.pop('username', None)  # limpa login anterior
    return render_template("index.html")

# Rota Login
@app.route("/login", methods=["GET", "POST"])
def login():
    return Usuario.login_usuario()


# Página de cadastro
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    return Usuario.cadastro_usuario()


# Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html", username=session['username'])
    return redirect(url_for('login'))


# Logout
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

    usuario = Usuario.query.filter_by(username=session["username"]).first()

    termo = request.args.get("q", "").strip().lower()

    # 🔹 1. Busca intolerâncias do usuário
    intolerancias = (
        db.session.query(Ingrediente.id_ingrediente)
        .join(Intolerancia, Ingrediente.id_ingrediente == Intolerancia.fk_ingrediente)
        .filter(Intolerancia.fk_usuario == usuario.id_usuario)
        .all()
    )
    intolerancia_ids = [i[0] for i in intolerancias]

    # 🔹 2. Base da query de receitas
    query = Receita.query

    # 🔹 3. Filtro por nome de receita (busca)
    if termo:
        query = query.filter(func.lower(Receita.titulo).like(f"%{termo}%"))

    # 🔹 4. Se houver intolerâncias, exclui receitas que as contenham
    if intolerancia_ids:
        query = query.filter(
            ~Receita.id.in_(
                db.session.query(IngredienteReceita.fk_receita)
                .filter(IngredienteReceita.fk_ingrediente.in_(intolerancia_ids))
            )
        )

    receitas = query.all()

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


@app.route("/favoritar/<int:receita_id>", methods=["POST"])
def favoritar(receita_id):
    if "username" not in session:
        return redirect(url_for("home"))

    usuario = Usuario.query.filter_by(username=session["username"]).first()
    favorito_existente = Favorito.query.filter_by(fk_usuario=usuario.id_usuario, fk_receita=receita_id).first()

    if favorito_existente:
        # Se já estiver favoritado, remove (desfavorita)
        db.session.delete(favorito_existente)
        db.session.commit()
    else:
        # Caso contrário, adiciona
        novo_favorito = Favorito(fk_usuario=usuario.id_usuario, fk_receita=receita_id)
        db.session.add(novo_favorito)
        db.session.commit()

    return redirect(url_for("explorar"))


@app.route("/favoritos")
def favoritos():
    if "username" not in session:
        return redirect(url_for("home"))

    usuario = Usuario.query.filter_by(username=session["username"]).first()

    # 🔍 Recebe o termo de busca da barra de pesquisa
    termo = request.args.get("q", "").strip().lower()

    # Base da query
    query = (
        db.session.query(Receita)
        .join(Favorito, Receita.id == Favorito.fk_receita)
        .filter(Favorito.fk_usuario == usuario.id_usuario)
    )

    # Se tiver texto na busca, filtra
    if termo:
        query = query.filter(func.lower(Receita.titulo).like(f"%{termo}%"))

    receitas = query.all()

    return render_template("favoritos.html", receitas=receitas, termo=termo)


@app.route("/preferencias", methods=["GET", "POST"])
def preferencias():
    if "username" not in session:
        return redirect(url_for("home"))

    usuario = Usuario.query.filter_by(username=session["username"]).first()

    # Ingredientes comuns fixos
    ingredientes_comuns = [
        "Trigo", "Aveia", "Cevada", "Centeio",
        "Leite", "Ovo", "Bacalhau", "Marisco", "Arenque",
        "Camarão", "Carne bovina", "Tomate", "Espinafre",
        "Banana", "Nozes", "Couve", "Morango",
        "Chocolate", "Refrigerante à base de cola",
        "Amendoim", "Castanha"
    ]

    if request.method == "POST":
        selecionados = request.form.getlist("intolerancias")

        # Limpa preferências antigas
        Intolerancia.query.filter_by(fk_usuario=usuario.id_usuario).delete()

        # Verifica se ingrediente existe no banco antes de relacionar
        for nome in selecionados:
            ingrediente = Ingrediente.query.filter(func.lower(Ingrediente.nome_ingrediente) == nome.lower()).first()
            if ingrediente:
                nova_intolerancia = Intolerancia(
                    fk_usuario=usuario.id_usuario,
                    fk_ingrediente=ingrediente.id_ingrediente
                )
                db.session.add(nova_intolerancia)

        db.session.commit()
        return redirect(url_for("preferencias"))

    # 🔍 Buscar intolerâncias já salvas do usuário
    intolerancias_usuario = (
        db.session.query(Ingrediente.nome_ingrediente)
        .join(Intolerancia, Ingrediente.id_ingrediente == Intolerancia.fk_ingrediente)
        .filter(Intolerancia.fk_usuario == usuario.id_usuario)
        .all()
    )

    # Converte para uma lista de nomes (ex: ["Leite", "Amendoim"])
    intolerancias_usuario = [i[0].lower() for i in intolerancias_usuario]

    return render_template(
        "preferencias.html",
        ingredientes_comuns=ingredientes_comuns,
        intolerancias_usuario=intolerancias_usuario
    )



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

