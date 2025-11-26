from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from sqlalchemy import text
from bk_usuario import db, Usuario  # Import do models
import os
from bk_usuario import db, Usuario  # Import do models
from bk_receita import Receita, listar_receitas_usuario, Avaliacao
from sqlalchemy import func
from bk_receita import Ingrediente
from bk_receita import IngredienteReceita
from bk_usuario import Favorito, Intolerancia
import pickle
from treinar_modelo import treinar_modelo

from werkzeug.utils import secure_filename

import pickle
import random

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

    # ❌ Bloqueia se o usuário for o autor
    if receita.fk_usuario == user.id_usuario:
        return redirect(url_for("detalhe_receita", id=id))

    nota = int(request.form["nota"])
    comentario = request.form.get("comentario", "")

    Avaliacao.salvar_avaliacao(user.id_usuario, id, nota, comentario)

    # 🔥 Verifica se precisa re-treinar
    from treinar_modelo import treinar_modelo
    treinar_modelo()


    return redirect(url_for("detalhe_receita", id=id))




@app.route("/nova_receita", methods=["GET", "POST"])
def nova_receita():
    if "username" not in session:
        return redirect(url_for("login"))

    # GET normal → abre página vazia
    if request.method == "GET":
        return render_template("nova_receita.html")

    # POST → CRIAR ou EDITAR
    id_receita = request.form.get("id_receita")
    titulo = request.form["titulo"]

    # IMAGEM
    file = request.files.get("imagem")
    imagem_path = None

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        imagem_path = f"imagens_receitas/{filename}"

    instrucoes = request.form["instrucoes"]
    categoria = request.form["categoria"]
    utensilios = request.form["utensilios"]

    user = Usuario.query.filter_by(username=session["username"]).first()

    # --------------------------
    #  SE TEM ID → EDITAR
    # --------------------------
    if id_receita:
        receita = Receita.query.get(id_receita)

        receita.titulo = titulo
        receita.instrucoes = instrucoes
        receita.categoria = categoria
        receita.utensilios = utensilios

        if imagem_path:
            receita.imagem = imagem_path

        # apaga ingredientes antigos
        IngredienteReceita.query.filter_by(fk_receita=id_receita).delete()
        db.session.commit()

    else:
        # --------------------------
        #  SENÃO → CRIAR NOVA
        # --------------------------
        receita = Receita(
            titulo=titulo,
            imagem=imagem_path,
            instrucoes=instrucoes,
            categoria=categoria,
            utensilios=utensilios,
            fk_usuario=user.id_usuario
        )
        db.session.add(receita)
        db.session.commit()

    # INGREDIENTES
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
                fk_receita=receita.id,
                fk_ingrediente=ingrediente.id_ingrediente,
                quantidade_ingrediente_receita=qtd
            )
            db.session.add(relacao)

    db.session.commit()

    return redirect(url_for("explorar"))





@app.route("/minhas_receitas")
def minhas_receitas():
    if "username" not in session:
        return redirect(url_for("login"))

    user = Usuario.query.filter_by(username=session["username"]).first()
    q = request.args.get("q", "").strip()  # termo de busca

    receitas = listar_receitas_usuario(user.id_usuario)

    # 🔍 Filtra receitas se houver termo de busca
    if q:
        receitas = [r for r in receitas if q.lower() in r.titulo.lower()]

    return render_template("minhas_receitas.html", receitas=receitas)

@app.route("/remover_receita/<int:id>")
def remover_receita(id):
    print("SESSION:", session)

    if "username" not in session:
        return redirect(url_for("login"))

    receita = Receita.query.get(id)

    if not receita:
        return "Receita não encontrada"

    print("Receita fk_usuario:", receita.fk_usuario)
    print("Session id_usuario:", session.get("id_usuario"))

    # Verifica se a receita pertence ao usuário logado
    if receita.fk_usuario != session.get("id_usuario"):
        return "Acesso negado"

    # 🔥 1. Remove favoritos relacionados a esta receita
    Favorito.query.filter_by(fk_receita=id).delete()

    # 🔥 2. Remove ingredientes da receita
    for ing in receita.ingredientes_receita:
        db.session.delete(ing)

    # 🔥 3. Remove também avaliações relacionadas
    Avaliacao.query.filter_by(fk_receita=id).delete()

    # 🔥 4. Agora sim, remove a receita
    db.session.delete(receita)

    db.session.commit()

    return redirect(url_for("minhas_receitas"))




@app.route("/editar_receita/<int:id>", methods=["GET"])
def editar_receita(id):
    receita = Receita.query.get(id)
    return render_template("nova_receita.html", receita=receita)




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
        
    # 🔄 Atualiza o modelo após cada mudança nos favoritos
    os.system("python treinar_modelo.py")

    return redirect(url_for("explorar"))

@app.route("/remover_favorito/<int:receita_id>", methods=["POST"])
def remover_favorito(receita_id):
    if "username" not in session:
        return jsonify({"erro": "Usuário não autenticado"}), 403

    usuario = Usuario.query.filter_by(username=session["username"]).first()

    favorito = Favorito.query.filter_by(
        fk_usuario=usuario.id_usuario,
        fk_receita=receita_id
    ).first()

    if favorito:
        db.session.delete(favorito)
        db.session.commit()
        return jsonify({"sucesso": True}), 200

    return jsonify({"erro": "Favorito não encontrado"}), 404


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

# 🔹 Carrega preferências salvas
preferencias = None
if os.path.exists("preferencias_usuarios.pkl"):
    with open("preferencias_usuarios.pkl", "rb") as f:
        preferencias = pickle.load(f)
    print("✅ Preferências carregadas com sucesso!")
else:
    print("⚠️ Nenhuma preferência encontrada. Execute treinar_modelo.py primeiro.")


@app.route("/recomendacoes")
def recomendacoes():
    # =====================
    # 1) Verificar Login
    # =====================
    if "username" not in session:
        return redirect(url_for("home"))

    usuario = Usuario.query.filter_by(username=session["username"]).first()

    # =====================
    # 2) Tentar carregar modelos
    # =====================
    try:
        with open("modelo_recomendacao.pkl", "rb") as f:
            similaridade = pickle.load(f)

        with open("preferencias_categorias.pkl", "rb") as f:
            preferencias_categoria = pickle.load(f)
            
        with open("media_receitas.pkl", "rb") as f:
            medias = pickle.load(f)
            
    except:
        similaridade = None
        preferencias_categoria = {}
        medias = {}

    # =====================
    # 3) Se o usuário não tem modelo → usar favoritos antigos
    # =====================
    categoria_prevista = preferencias_categoria.get(usuario.id_usuario, None)

    if similaridade is None or similaridade.empty:
        print("⚠️ Usuário sem histórico avaliativo → usando favoritos/aleatório.")

        receitas_recomendadas = (
            db.session.query(Receita)
            .order_by(func.rand())
            .limit(6)
            .all()
        )
    else:
        # =====================
        # 4) Filtragem colaborativa (modelo de notas)
        # =====================
        # Receitas já avaliadas pelo usuário (não repetir)
        # Receitas mal avaliadas pelo usuário devem ser removidas do ranking
        mal_avaliadas = (
            db.session.query(Avaliacao.fk_receita)
            .filter(Avaliacao.fk_usuario == usuario.id_usuario, Avaliacao.nota <= 2)
            .all()
        )
        mal_avaliadas = [m[0] for m in mal_avaliadas]

        # Receitas já avaliadas (qualquer nota) também não serão sugeridas
        # Receitas já avaliadas (qualquer nota) também não serão sugeridas
        avaliadas = (
            db.session.query(Avaliacao.fk_receita)
            .filter_by(fk_usuario=usuario.id_usuario)
            .all()
        )
        avaliadas = [a[0] for a in avaliadas]

        # Receitas favoritedas
        favoritadas = (
            db.session.query(Favorito.fk_receita)
            .filter_by(fk_usuario=usuario.id_usuario)
            .all()
        )
        favoritadas = [f[0] for f in favoritadas]

        # Receitas criadas pelo próprio usuário (NÃO recomendar)
        criadas_por_usuario = (
            db.session.query(Receita.id)
            .filter(Receita.fk_usuario == usuario.id_usuario)
            .all()
        )
        criadas_por_usuario = [c[0] for c in criadas_por_usuario]

        # Remove todas: avaliadas, mal avaliadas e criadas pelo próprio usuário
        # Remover receitas avaliadas (qualquer nota), mal avaliadas e criadas pelo usuário
        remover = set(avaliadas + mal_avaliadas + favoritadas + criadas_por_usuario)
        similaridade_filtrada = similaridade.drop(
            index=list(remover), 
            columns=list(remover), 
            errors="ignore"
        )


        # ---- CÁLCULO DO SCORE FINAL ----
        # média de similaridade de cada receita com as demais, após filtro
        sim = similaridade_filtrada.mean(axis=1)
        
        # Dar bônus para receitas da categoria favorita
        if categoria_prevista:
            categorias = {r.id: r.categoria for r in Receita.query.filter(Receita.id.in_(sim.index)).all()}
            for r in sim.index:
                if categorias[r] == categoria_prevista:
                    sim[r] *= 1.25  # +25% de peso



        for r in sim.index:
            if r in medias:
                sim[r] *= (medias[r] / max(medias.values()))

        recomendadas_ids = sim.sort_values(ascending=False).head(10).index.tolist()

        
        # =====================
        # 5) Filtro pela categoria favorita (se possível)
        # =====================
        receitas_recomendadas = (
            db.session.query(Receita)
            .filter(Receita.id.in_(recomendadas_ids))
            .filter(~Receita.id.in_(mal_avaliadas))
            .filter(~Receita.id.in_(avaliadas))
            .filter(Receita.fk_usuario != usuario.id_usuario)
            .limit(6)
            .all()
        )

        # Caso não tenha sugestões nessa categoria → ainda recomendar outras
        if not receitas_recomendadas:
            receitas_recomendadas = (
                db.session.query(Receita)
                .filter(Receita.id.in_(recomendadas_ids))
                .filter(~Receita.id.in_(mal_avaliadas))
                .filter(~Receita.id.in_(avaliadas))
                .filter(Receita.fk_usuario != usuario.id_usuario)
                .limit(6)
                .all()
            )

        # Como fallback final → aleatórias
        if not receitas_recomendadas:
            receitas_recomendadas = (
                db.session.query(Receita)
                .order_by(func.rand())
                .limit(6)
                .all()
            )

    # =====================
    # 6) Retornar JSON para o frontend
    # =====================
    dados = [
        {
            "id": r.id,
            "titulo": r.titulo,
            "imagem": r.imagem,
            "categoria": r.categoria
        }
        for r in receitas_recomendadas
    ]

    return jsonify(dados)

def verificar_treinamento():
    # Conta avaliações que ainda não foram treinadas
    novas = Avaliacao.query.filter_by(treinado=False).count()
    
    # Treina se tiver >= 10
    if novas >= 10:
        treinar_modelo()
        print(f"🤖 Modelo re-treinado automaticamente com {novas} novas avaliações!")


    
@app.route("/retrain_model")
def retrain_model():
    os.system("python treinar_modelo.py")
    return "Modelo re-treinado com sucesso!"



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

