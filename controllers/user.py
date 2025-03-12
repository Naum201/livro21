from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, flash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func, desc, literal
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from werkzeug.utils import secure_filename
from functools import wraps
import os
import re
from docx import Document
from app import Usuario, Seguidores, Obra, Capitulo, Comentario, Voto, Genero, Postagem, Notificacao, EngajamentoMensal, Mensagem, Suporte, ProjetoLeitura
from flask import g  # Importa o g para armazenar a variável temporária
from sqlalchemy.orm import joinedload

# Função para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:  # Verifica se o 'user_id' existe na sessão
            flash('Você precisa estar logado para acessar esta página.', 'danger')
            return redirect(url_for('login'))  # Redireciona para o login se não estiver logado
        return f(*args, **kwargs)
    return decorated_function

palavras_ofensivas = {
    "racismo": ["racista", "negrinho", "macaco", "preto sujo", "escravo", "favela"],
    "homofobia": ["viado", "bicha", "sapatão", "gay doente", "homossexual nojento"],
    "preconceito": ["feia", "gorda", "baleia", "miserável", "imbecil", "idiota"],
    "xenofobia": ["estrangeiro", "gringo", "alienígena", "imigrante nojento", "nacionalidade inferior"],
    "agressoes_verbais": ["idiota", "burro", "desgraçado", "filho da puta", "puta", "merda"],
    "discriminacao_genero": ["mulherzinha", "fruta", "feminazi", "machista", "cachorra", "macho escroto"],
    "odio": ["nojento", "lixo", "sujo", "verme", "lixo humano"]
}

# Função para verificar se o comentário contém palavras ofensivas
def verificar_comentario_ofensivo(comentario):
    for palavra in palavras_ofensivas:
        if re.search(r'\b' + re.escape(palavra) + r'\b', comentario, re.IGNORECASE):
            return True
    return False

# Função para verificar se o comentário contém palavras ofensivas
def verificar_comentario_ofensivo(comentario):
    for palavra in palavras_ofensivas:
        if re.search(r'\b' + re.escape(palavra) + r'\b', comentario, re.IGNORECASE):
            return True
    return False

# Função para notificar administradores
def notificar_administradores(comentario):
    # Lógica para enviar alerta aos administradores, pode ser via e-mail ou outra notificação
    # Exemplo:
    # send_email_to_admins(f"Comentário suspeito: {comentario}")
    print(f"Alerta: Comentário suspeito detectado: {comentario}")
@app.before_request
@app.before_request
def before_request():
    # Definindo um usuário logado (caso haja na sessão)
    usuario_logado_id = session.get('user_id')
    
    if usuario_logado_id:
        usuario_logado_id = int(usuario_logado_id)  # Garantir que seja um inteiro
        g.usuario_logado = Usuario.query.get_or_404(usuario_logado_id)
    else:
        g.usuario_logado = None
# Rota de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):
            session['user_id'] = usuario.id  # Armazena o ID do usuário na sessão
            return redirect(url_for('home'))  # Redireciona para a página inicial
        else:
            return render_template('login.html', error='Credenciais inválidas.')

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Verificar se o email já existe
        if Usuario.query.filter_by(email=email).first():
            return render_template('cadastro.html', error='Email já cadastrado.')

        # Criar novo usuário
        novo_usuario = Usuario(username=username, email=email, password=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()

        # Armazenar o ID do usuário na sessão para manter o usuário logado
        session['user_id'] = novo_usuario.id

        # Redirecionar para o formulário de participante do projeto de leitura
        return redirect(url_for('participa_projeto'))

    return render_template('cadastro.html')

@app.route('/participa_projeto', methods=['GET', 'POST'])
def participa_projeto():
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('login'))  # Redireciona para a página de login se o usuário não estiver logado
    
    if request.method == 'POST':
        resposta = request.form.get('participa_projeto')

        if resposta == 'sim':
            # Se o usuário participa, redireciona para o formulário
            return redirect(url_for('formulario_participante'))
        else:
            # Caso contrário, redireciona para a página inicial
            return redirect(url_for('home'))
    
    return render_template('usuario/participa_projeto.html')  # A página que pergunta se o usuário participa
@app.route('/formulario_participante', methods=['GET', 'POST'])
def formulario_participante():
    if 'user_id' not in session:
        flash("Você precisa estar logado para criar ou participar de um projeto de leitura.", "warning")
        return redirect(url_for('login'))  # Redireciona para login se o usuário não estiver logado

    # Recuperar o usuário logado
    usuario = Usuario.query.get(session['user_id'])

    # Verificar se o usuário já tem um projeto associado
    projeto_existente = ProjetoLeitura.query.filter(ProjetoLeitura.usuario_id == usuario.id).first()

    # Recuperar todos os projetos cadastrados
    projetos = ProjetoLeitura.query.all()

    if request.method == 'POST':
        nome_projeto = request.form.get('nome_projeto')
        admin_projeto = request.form.get('admin_projeto')
        descricao = request.form.get('descricao')
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        projeto_existente_id = request.form.get('projeto_existente')  # ID do projeto existente

        if projeto_existente_id:  # Se o usuário escolheu um projeto existente
            projeto = ProjetoLeitura.query.get(projeto_existente_id)
            if projeto:
                # Adiciona o usuário ao projeto existente
                if usuario not in projeto.usuarios:
                    projeto.usuarios.append(usuario)
                    db.session.commit()
                    flash(f"Você foi adicionado ao projeto {projeto.nome}.", "success")
                else:
                    flash("Você já está nesse projeto!", "info")
            else:
                flash("Projeto selecionado não encontrado.", "danger")
            return redirect(url_for('home'))  # Redireciona após adicionar ao projeto

        else:  # Se o usuário deseja criar um novo projeto
            if not nome_projeto or not admin_projeto or not descricao:
                flash("Todos os campos obrigatórios devem ser preenchidos.", "danger")
                return redirect(url_for('formulario_participante'))

            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d') if data_inicio else None
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else None
            except ValueError:
                flash("Formato de data inválido. Use YYYY-MM-DD.", "danger")
                return redirect(url_for('formulario_participante'))

            # Criar novo projeto
            novo_projeto = ProjetoLeitura(
                nome=nome_projeto,
                admin_projeto=admin_projeto,
                descricao=descricao,
                data_inicio=data_inicio,
                data_fim=data_fim,
                usuario_id=usuario.id  # Associando o projeto ao usuário logado
            )

            try:
                db.session.add(novo_projeto)
                db.session.commit()

                # Associar o criador ao projeto
                novo_projeto.usuarios.append(usuario)
                db.session.commit()

                flash("Projeto criado com sucesso!", "success")
                return redirect(url_for('home'))
            except Exception as e:
                db.session.rollback()
                flash(f"Erro ao criar o projeto: {str(e)}", "danger")

    return render_template(
        'usuario/formulario_participante.html',
        projetos=projetos,
        projeto_existente=projeto_existente
    )

def atualizar_engajamento_mensal():
    mes_atual = datetime.now().strftime('%Y-%m')
    obras = Obra.query.filter_by(status='Publicado').all()

    for obra in obras:
        # Calcule as métricas de engajamento (exemplo: contagens fictícias)
        visualizacoes = obra.visualizacoes  # Supondo que o modelo Obra tenha este campo
        votos = obra.votos  # Supondo que o modelo Obra tenha este campo
        comentarios = len(obra.comentarios)  # Supondo relacionamento com um modelo Comentario

        total_engajamento = visualizacoes + votos + comentarios

        # Crie ou atualize o registro mensal
        engajamento = EngajamentoMensal.query.filter_by(obra_id=obra.id, mes=mes_atual).first()
        if not engajamento:
            engajamento = EngajamentoMensal(
                obra_id=obra.id,
                mes=mes_atual,
                visualizacoes=visualizacoes,
                votos=votos,
                comentarios=comentarios,
                total_engajamento=total_engajamento
            )
            db.session.add(engajamento)
        else:
            engajamento.visualizacoes = visualizacoes
            engajamento.votos = votos
            engajamento.comentarios = comentarios
            engajamento.total_engajamento = total_engajamento

    db.session.commit()


@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['user_id']
    usuario = Usuario.query.get(usuario_id)
     # Obtendo o usuário logado
    usuario_logado_id = session.get('user_id')
    if usuario_logado_id:
        usuario_logado = Usuario.query.get_or_404(usuario_logado_id)
    else:
        usuario_logado = None  # Caso não exista um usuário logado
    # Obter obras do usuário que estão publicadas
    obras_usuario = Obra.query.filter_by(usuario_id=usuario_id, status='Publicado').all()

    # Obter gêneros e obras publicadas
    generos = Genero.query.all()
    obras_por_genero = [
        {"genero": genero.nome, "obras": Obra.query.filter_by(genero_id=genero.id, status='Publicado').all()}
        for genero in generos
    ]

    # Obter as obras mais lidas que estão publicadas
    obras_mais_lidas = Obra.query.filter_by(status='Publicado').order_by(Obra.visualizacoes.desc()).limit(5).all()

    # Verificar se estamos nas duas primeiras semanas do mês
    hoje = datetime.today()
    if hoje.day <= 30:  # Alterar conforme o período desejado
        concurso_ativo = True
    else:
        concurso_ativo = False

    # Calcular engajamento mensal
    engajamentos_mensais = []
    if concurso_ativo:
        engajamentos_mensais = (
            db.session.query(
                Obra.id.label('id'),
                Obra.titulo.label('titulo'),
                Obra.capa.label('capa'),
                func.sum(Capitulo.visualizacoes).label('visualizacoes'),
                func.sum(Capitulo.votos).label('votos'),
                func.count(Comentario.id).label('comentarios'),
                (
                    (func.sum(Capitulo.visualizacoes) * 0.5) +
                    (func.sum(Capitulo.votos) * 2) +
                    (func.count(Comentario.id) * 2.5)
                ).label('engajamento_total')
            )
            .join(Capitulo, Obra.id == Capitulo.obra_id)
            .outerjoin(Comentario, Obra.id == Comentario.obra_id)
            .filter(Obra.status == 'Publicado')
            .group_by(Obra.id)
            .order_by(desc('engajamento_total'))
            .limit(3)
            .all()
        )

    return render_template(
    'usuario/home.html',
    usuario=usuario,
    usuario_logado=usuario_logado,  # Corrigido
    obras_usuario=obras_usuario,
    obras_por_genero=obras_por_genero,
    obras_mais_lidas=obras_mais_lidas,
    concurso_ativo=concurso_ativo,
    engajamentos_mensais=engajamentos_mensais
)

# Logout
@app.route('/logout')
def logout():
    # Remover a sessão do usuário
    session.pop('user_id', None)  # Isso remove o 'user_id' da sessão, efetivamente desconectando o usuário
    flash('Você foi desconectado com sucesso!', 'success')
    return redirect(url_for('login'))  # Redireciona para a página de login


@app.route('/perfil/<int:user_id>', methods=['GET', 'POST'])
def perfil(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    obras = Obra.query.filter_by(usuario_id=user_id).all()
    seguidores = Seguidores.query.filter_by(seguido_id=user_id).all()
    postagens = Postagem.query.filter_by(usuario_id=user_id).order_by(Postagem.data_postagem.desc()).all()

    # Obtendo o usuário logado
    usuario_logado_id = session.get('user_id')
    if usuario_logado_id:
        usuario_logado = Usuario.query.get_or_404(usuario_logado_id)
    else:
        usuario_logado = None  # Caso não exista um usuário logado

    if request.method == 'POST':
        # Verificando se é uma postagem
        if 'titulo' in request.form and 'conteudo' in request.form:
            titulo = request.form['titulo']
            conteudo = request.form['conteudo']

            # Criar nova postagem associada ao perfil do escritor
            nova_postagem = Postagem(
                titulo=titulo,
                conteudo=conteudo,
                usuario_id=usuario_logado.id  # Associando a postagem ao escritor
            )
            db.session.add(nova_postagem)
            db.session.commit()

            # Criar notificações
            mensagem = f"Novo post publicado por {usuario_logado.username}: {titulo}"

            # Notificação para o próprio usuário
            nova_notificacao = Notificacao(
                mensagem=mensagem,
                usuario_id=usuario_logado.id
            )
            db.session.add(nova_notificacao)

            # Notificação para os seguidores
            for seguidor in seguidores:
                if seguidor.seguidor_id != usuario_logado.id:  # Evitar notificar o próprio usuário
                    nova_notificacao_seguidor = Notificacao(
                        mensagem=mensagem,
                        usuario_id=seguidor.seguidor_id
                    )
                    db.session.add(nova_notificacao_seguidor)

            db.session.commit()

            flash('Postagem criada com sucesso!', 'success')

        # Verificando se é um upload de foto de perfil
        if 'foto_perfil' in request.files:
            foto_perfil = request.files['foto_perfil']
            if foto_perfil.filename:
                filename = secure_filename(foto_perfil.filename)
                caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto_perfil.save(caminho_foto)

                usuario_logado.imagens = filename  # Atualiza a imagem no banco de dados
                db.session.commit()
                flash('Foto de perfil atualizada com sucesso!', 'success')

        # Redireciona após a submissão
        return redirect(url_for('perfil', user_id=usuario_logado.id))

    return render_template('usuario/perfil.html', usuario=usuario, obras=obras, seguidores=seguidores, postagens=postagens, usuario_logado=usuario_logado)

@app.route('/seguidores/<int:user_id>')
def seguidores(user_id):
    # Buscar o usuário pelo ID
    usuario = Usuario.query.get_or_404(user_id)
    obras = Obra.query.filter_by(usuario_id=user_id).all()
    seguidores = Seguidores.query.filter_by(seguido_id=user_id).all()
    postagens = Postagem.query.filter_by(usuario_id=user_id).order_by(Postagem.data_postagem.desc()).all()    
    # Buscar seguidores do usuário
    seguidores = Seguidores.query.filter_by(seguido_id=user_id).all()

    # Obtendo o usuário logado
    usuario_logado_id = session.get('user_id')
    usuario_logado = Usuario.query.get_or_404(usuario_logado_id) if usuario_logado_id else None
    postagens = Postagem.query.options(joinedload(Postagem.usuario)).all()
    if request.method == 'POST':
        # Verificando se é uma postagem e associando ao perfil do escritor
        if 'titulo' in request.form and 'conteudo' in request.form:
            titulo = request.form['titulo']
            conteudo = request.form['conteudo']

            # Criar nova postagem associada ao perfil do escritor
            nova_postagem = Postagem(
                titulo=titulo,
                conteudo=conteudo,
                usuario_id=usuario.id  # Associando a postagem ao escritor
            )
            db.session.add(nova_postagem)
            db.session.commit()

            flash('Postagem criada com sucesso!', 'success')
    # Passando os dados para o template
    return render_template('usuario/perfil.html', usuario=usuario, obras=obras, seguidores=seguidores, postagens=postagens, usuario_logado=usuario_logado)

@app.route('/perfil/editar', methods=['GET', 'POST'])
def editar_perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['user_id']
    usuario = Usuario.query.get(usuario_id)    
    if request.method == 'POST':
        if 'imagens' in request.files:
            imagens = request.files['imagens']
            if imagens:
                # Save the image with a secure filename
                imagem_filename = secure_filename(imagens.filename)
                imagens.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_filename))
                usuario.imagens = imagem_filename  # Update the user profile image
        db.session.commit()  # Save changes to the database
        
    return render_template('usuario/editar_perfil.html', usuario=usuario)

@app.route('/visualizacao_capitulo/<int:capitulo_id>', methods=['GET', 'POST'])
def visualizacao_capitulo(capitulo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona se o usuário não estiver logado

    usuario_id = session['user_id']
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        flash('Usuário não encontrado!', 'danger')
        return redirect(url_for('home'))  # Se o usuário não existir, redireciona para home

    # Buscar o capítulo pelo ID
    capitulo = Capitulo.query.get_or_404(capitulo_id)
    obra = capitulo.obra  # Obter a obra associada ao capítulo

    # Contabilizar visualização caso o usuário não seja o autor da obra
    if usuario_id != obra.usuario_id:
        capitulo.visualizacoes += 1

    # Verificar se o usuário já votou neste capítulo
    voto_existente = Voto.query.filter_by(usuario_id=usuario_id, capitulo_id=capitulo_id).first()

    if request.method == 'POST':
        if 'voto' in request.form and voto_existente is None:
            # Registrar voto
            novo_voto = Voto(usuario_id=usuario_id, capitulo_id=capitulo_id)
            db.session.add(novo_voto)
            capitulo.votos += 1
            flash('Voto registrado com sucesso!', 'success')
        
        elif 'voto' in request.form:
            flash('Você já votou neste capítulo!', 'danger')

        # Verificar se é um comentário
        if 'comentario' in request.form:
            texto_comentario = request.form['comentario'].strip()
            if texto_comentario:
                # Verifica se o comentário contém palavras ofensivas
                if verificar_comentario_ofensivo(texto_comentario):
                    # Se o comentário for ofensivo, flash a mensagem de erro
                    flash('Comentário contém conteúdo inadequado e não será enviado. Por favor, revise!', 'danger')
                else:
                    # Caso contrário, registra o comentário
                    novo_comentario = Comentario(
                        texto=texto_comentario,
                        usuario_id=usuario_id,
                        capitulo_id=capitulo_id,
                        obra_id=obra.id
                    )
                    db.session.add(novo_comentario)
                    flash('Comentário adicionado com sucesso!', 'success')

        db.session.commit()  # Um único commit para melhor performance

    # Buscar os comentários do capítulo
    comentarios = Comentario.query.filter_by(capitulo_id=capitulo_id).all()

    return render_template(
        'usuario/visualizacao_capitulo.html', 
        capitulo=capitulo, 
        usuario_logado=usuario,  # Corrigido para usuario_logado
        comentarios=comentarios,
        voto_existente=voto_existente
    )


@app.route('/caixa_de_entrada', methods=['GET', 'POST'])
def caixa_de_entrada():
    # Obtendo o usuário logado
    usuario_logado_id = session.get('user_id')
    usuario_logado = Usuario.query.get(usuario_logado_id) if usuario_logado_id else None

    # Inicializamos a lista de conversas e usuários_pesquisados
    conversas = []
    usuarios_pesquisados = []  # Garantir que a variável seja sempre definida

    if usuario_logado:
        # Se a requisição for uma busca, procuramos por usuários
        if request.method == 'POST':
            pesquisa = request.form.get('pesquisa')
            # Realiza a busca de conversas, excluindo o próprio usuário
            conversas = db.session.query(Mensagem, Usuario).join(Usuario, Usuario.id == Mensagem.usuario_id).filter(
                ((Mensagem.usuario_id == usuario_logado.id) | (Mensagem.destinatario_id == usuario_logado.id)) &
                (Usuario.id != usuario_logado.id)  # Garantir que o usuário logado não apareça
            ).group_by(Mensagem.destinatario_id).all()

            # Filtrando os usuários conforme a pesquisa, mas excluindo o próprio usuário
            usuarios_pesquisados = Usuario.query.filter(
                Usuario.username.like(f'%{pesquisa}%') & (Usuario.id != usuario_logado.id)  # Excluir o usuário logado
            ).all()
        else:
            # Caso contrário, buscamos todas as conversas, excluindo o próprio usuário
            conversas = db.session.query(Mensagem, Usuario).join(Usuario, Usuario.id == Mensagem.usuario_id).filter(
                ((Mensagem.usuario_id == usuario_logado.id) | (Mensagem.destinatario_id == usuario_logado.id)) &
                (Usuario.id != usuario_logado.id)  # Excluir o próprio usuário
            ).group_by(Mensagem.destinatario_id).all()

    return render_template('usuario/caixa_de_entrada.html', usuario_logado=usuario_logado, conversas=conversas, usuarios_pesquisados=usuarios_pesquisados)


@app.route('/chat/<int:id>', methods=['GET', 'POST'])
def chat(id):
    usuario_logado_id = session.get('user_id')
    usuario_logado = Usuario.query.get(usuario_logado_id) if usuario_logado_id else None
    destinatario = Usuario.query.get(id)

    if usuario_logado and destinatario:
        if request.method == 'POST':
            mensagem_texto = request.form.get('mensagem')
            nova_mensagem = Mensagem(
                texto=mensagem_texto,
                usuario_id=usuario_logado.id,  # Usando 'usuario_id' em vez de 'remetente_id'
                destinatario_id=destinatario.id
            )
            db.session.add(nova_mensagem)
            db.session.commit()

        # Buscando todas as mensagens entre o usuário logado e o destinatário
        mensagens = Mensagem.query.filter(
            (Mensagem.usuario_id == usuario_logado.id) & (Mensagem.destinatario_id == destinatario.id) |
            (Mensagem.usuario_id == destinatario.id) & (Mensagem.destinatario_id == usuario_logado.id)
        ).order_by(Mensagem.timestamp).all()  # Alterando 'data_envio' para 'timestamp' conforme seu modelo

    return render_template('usuario/chat.html', usuario_logado=usuario_logado, destinatario=destinatario, mensagens=mensagens)

@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    usuario_logado_id = session.get('user_id')
    usuario_logado = Usuario.query.get(usuario_logado_id) if usuario_logado_id else None

    if request.method == 'POST':
        # Atualizar email, username, bio, data de nascimento
        novo_email = request.form.get('email')
        novo_username = request.form.get('username')
        nova_bio = request.form.get('bio')
        nova_data_nascimento = request.form.get('data_nascimento')

        # Atualizar configurações de notificações
        notificacoes = True if request.form.get('notificacoes') else False

        # Atualizar preferências de conteúdo (poderia ser um campo similar no modelo de preferências)
        preferencia_conteudo = request.form.get('preferencia_conteudo')

        # Verificar e atualizar a senha se fornecida
        nova_senha = request.form.get('senha')
        if nova_senha:
            usuario_logado.set_password(nova_senha)  # Atualizar a senha com hash

        # Inicializar o 'filename' com a imagem atual, caso não haja uma nova foto de perfil
        filename = usuario_logado.imagens

        # Atualizar a foto de perfil se houver um arquivo enviado
        if 'foto_perfil' in request.files:
            foto_perfil = request.files['foto_perfil']
            if foto_perfil:
                # Salvar a foto com um nome único
                filename = secure_filename(foto_perfil.filename)
                caminho_foto = os.path.join('static/uploads', filename)
                foto_perfil.save(caminho_foto)
                usuario_logado.imagens = filename  # Atualizar o caminho da foto

        # Atualizar informações no banco de dados (corrigir 'imagem' para 'imagens')
        usuario_logado.update_profile(username=novo_username, email=novo_email, bio=nova_bio,
                                      data_nascimento=nova_data_nascimento, imagens=filename)
        usuario_logado.notificacoes = notificacoes
        usuario_logado.preferencia_conteudo = preferencia_conteudo

        db.session.commit()  # Salvar as alterações no banco de dados
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('configuracoes'))

    # Caso seja GET, exibir o formulário com os dados atuais
    return render_template('usuario/configuracoes.html', usuario_logado=usuario_logado)

@app.route('/deletar_conta', methods=['POST'])
def deletar_conta():
    usuario_logado_id = session.get('user_id')
    usuario_logado = Usuario.query.get(usuario_logado_id) if usuario_logado_id else None

    if not usuario_logado:
        flash('Você precisa estar logado para deletar sua conta.', 'danger')
        return redirect(url_for('login'))  # Redirecionar para login se o usuário não estiver logado
    
    # Deletar a conta do usuário
    db.session.delete(usuario_logado)
    db.session.commit()

    # Remover a sessão (logoff)
    session.pop('user_id', None)

    flash('Sua conta foi deletada com sucesso!', 'success')
    return redirect(url_for('index'))  # Redirecionar para a página inicial ou qualquer outra página


@app.route('/suporte', methods=['GET', 'POST'])
def suporte():
    usuario_logado_id = session.get('user_id')
    usuario_logado = Usuario.query.get(usuario_logado_id) if usuario_logado_id else None

    if request.method == 'POST':
        problema = request.form.get('problema')
        
        if problema:
            # Criar uma nova instância de Suporte
            novo_problema = Suporte(usuario_id=usuario_logado.id, problema=problema)
            db.session.add(novo_problema)
            db.session.commit()

            flash('Problema reportado com sucesso. Nossa equipe entrará em contato em breve.', 'success')
            return redirect(url_for('suporte'))  # Redireciona de volta para o formulário

        else:
            flash('Por favor, descreva o problema para enviar.', 'danger')

    # Exibir o formulário
    return render_template('usuario/suporte.html', usuario_logado=usuario_logado)
