from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import re
from app import app, db
from datetime import datetime
import os
from docx import Document
from app import Admin, Usuario, Obra, Suporte, Genero, Plataforma, Plagio, ProjetoLeitura, GradeLeitura, Notificacao
from difflib import SequenceMatcher
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
import difflib


# Rota: Cadastro de Admin
@app.route('/admin/cadastro', methods=['GET', 'POST'])
def admin_cadastro():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        # Verifica se o admin já existe
        if Admin.query.filter_by(email=email).first():
            flash('Email já cadastrado!', 'danger')
            return redirect(url_for('admin_cadastro'))

        # Criar admin
        novo_admin = Admin(username=username, email=email, password=senha_hash)
        db.session.add(novo_admin)
        db.session.commit()
        flash('Cadastro realizado com sucesso!', 'success')
        return redirect(url_for('admin_home'))  # Redireciona para a home do admin

    return render_template('admin_cadastro.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        admin = Admin.query.filter_by(email=email).first()

        if admin and check_password_hash(admin.password, senha):
            session['admin_id'] = admin.id  # Salva o ID na sessão
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin_home'))  # Redireciona para a home do admin
        else:
            flash('Credenciais inválidas.', 'danger')  # Mensagem de erro caso a autenticação falhe

    return render_template('admin_login.html')


@app.route('/admin/home')
def admin_home():
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    admin = Admin.query.get(session['admin_id'])
    
    if not admin:
        flash('Admin não encontrado.', 'danger')
        return redirect(url_for('admin_login'))

    quantidade_livros = Obra.query.count()
    quantidade_usuarios = Usuario.query.filter_by(ativo=True).count() + Admin.query.count()
    quantidade_problemas = Suporte.query.count()
    quantidade_plataformas = Plataforma.query.count()
    quantidade_usuarios_sairam = Usuario.query.filter_by(ativo=False).count()
    quantidade_plagios = Plagio.query.count()
    tickets_plagio = Plagio.query.filter_by(status='Pendente').all()
    projetos_leituras = ProjetoLeitura.query.count()
    projetos_de_leituras = ProjetoLeitura.query.all()  # Alterado para .all() para pegar a lista de projetos
    generos = Genero.query.all()

    return render_template('admin/admin.html', admin=admin, 
                           quantidade_livros=quantidade_livros,
                           quantidade_usuarios=quantidade_usuarios,
                           quantidade_plataformas=quantidade_plataformas,
                           quantidade_problemas=quantidade_problemas,
                           quantidade_usuarios_sairam=quantidade_usuarios_sairam,
                           quantidade_plagios=quantidade_plagios,
                           tickets_plagio=tickets_plagio,
                           projetos_leituras=projetos_leituras,
                           generos=generos,
                           projetos_de_leituras=projetos_de_leituras)



# Rota: Logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    flash('Você saiu da conta.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/configuracoes_admin', methods=['GET', 'POST'])
def admin_configuracoes():
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    admin = Admin.query.get(session['admin_id'])
    return render_template('admin/configuracoes_admin.html', admin=admin)


@app.route('/admin/configuracoes_admin/cadastrar_genero', methods=['GET', 'POST'])
def cadastrar_genero():
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    # Recupera o admin logado
    admin = Admin.query.get(session['admin_id'])

    if request.method == 'POST':
        nome = request.form['nome']
        
        # Verifique se o gênero já existe antes de criar um novo
        if Genero.query.filter_by(nome=nome).first():
            flash('Este gênero já existe!', 'danger')
        else:
            # Crie o novo gênero
            novo_genero = Genero(nome=nome)
            db.session.add(novo_genero)
            db.session.commit()
            flash('Gênero cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_home'))  # Redireciona para a home após o cadastro

    # Passa o objeto admin para o template
    return render_template('admin/cadastrar_genero.html', admin=admin)


@app.route('/admin/configuracoes_admin/adicionar_plataforma', methods=['GET', 'POST'])
def adicionar_plataforma():
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    # Recupera o admin logado
    admin = Admin.query.get(session['admin_id'])

    if request.method == 'POST':
        nome = request.form['nome']
        
        # Verificar se a plataforma já existe
        if Plataforma.query.filter_by(nome=nome).first():
            flash('Plataforma já cadastrada.', 'danger')
        else:
            nova_plataforma = Plataforma(nome=nome)
            db.session.add(nova_plataforma)
            db.session.commit()
            flash('Plataforma cadastrada com sucesso!', 'success')

        return redirect(url_for('adicionar_plataforma'))

    return render_template('admin/adicionar_plataforma.html', admin=admin)


def verificar_plagio(nova_sinopse, sinopses_existentes):
    """
    Função para verificar se a nova sinopse possui plágio com base em sinopses existentes.
    Utiliza a função 'SequenceMatcher' da biblioteca difflib para comparar as sinopses.
    """
    for sinopse in sinopses_existentes:
        # Verifica a similaridade entre a nova sinopse e as existentes
        similaridade = difflib.SequenceMatcher(None, nova_sinopse, sinopse).ratio()
        
        # Se a similaridade for superior a 80%, consideramos como plágio
        if similaridade > 0.8:  # Valor de 80% de similaridade
            return True, sinopse  # Retorna verdadeiro e a obra similar

    return False, None


# Primeira rota
@app.route('/admin/projetos', methods=['GET'])
def listar_projetos():
    # Verifica se o admin está logado
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    # Recupera o admin logado
    admin = Admin.query.get(session['admin_id'])

    # Busca todos os projetos
    projetos = ProjetoLeitura.query.all()

    # Retorna o template com a listagem dos projetos
    return render_template('admin/projetos.html', projetos=projetos, admin=admin)


@app.route('/admin/projeto/<int:projeto_id>')
def detalhes_projeto(projeto_id):
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    admin = Admin.query.get(session['admin_id'])

    # Obter o projeto pelo ID
    projeto = ProjetoLeitura.query.get(projeto_id)
    if not projeto:
        flash('Projeto não encontrado.', 'danger')
        return redirect(url_for('admin_dashboard'))  # Página de erro

    participantes = projeto.usuarios  # ✅ Removido .all()
    quantidade_participantes = len(participantes)

    estatisticas_usuarios = []
    for participante in participantes:
        obras_usuario = Obra.query.filter_by(usuario_id=participante.id).all()
        numero_obras = len(obras_usuario)

        if numero_obras > 0:
            media_votos = sum(obra.votos for obra in obras_usuario) / numero_obras
            media_visualizacoes = sum(obra.visualizacoes for obra in obras_usuario) / numero_obras
            media_likes = sum(obra.likes for obra in obras_usuario) / numero_obras
        else:
            media_votos = media_visualizacoes = media_likes = 0

        numero_capitulos = sum(len(obra.capitulos) for obra in obras_usuario)

        estatisticas_usuarios.append({
            'usuario': participante,
            'numero_obras': numero_obras,
            'media_votos': media_votos,
            'media_visualizacoes': media_visualizacoes,
            'media_likes': media_likes,
            'numero_capitulos': numero_capitulos
        })

    grades = GradeLeitura.query.filter_by(projeto_id=projeto_id).all()

    grades_com_leitores = [{
        'grade': grade,
        'leitores': grade.leitores
    } for grade in grades]

    return render_template(
        'admin/projetos/detalhes_projeto.html',
        admin=admin,
        usuarios=participantes,
        projeto=projeto,
        total_participantes=quantidade_participantes,
        estatisticas_usuarios=estatisticas_usuarios,
        grades=grades_com_leitores
    )


@app.route('/admin/projeto/<int:projeto_id>/cadastrar_grade', methods=['GET', 'POST'])
def cadastrar_grade_leitura(projeto_id):
    if 'admin_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('admin_login'))

    admin = Admin.query.get(session['admin_id'])
    projeto = ProjetoLeitura.query.get_or_404(projeto_id)
    obras_disponiveis = Obra.query.all()

    if request.method == 'POST':
        obra_id = request.form['obra_id']
        obra = Obra.query.get(obra_id)

        # Verifica se a obra já está na grade
        if GradeLeitura.query.filter_by(projeto_id=projeto.id, obra_id=obra.id).first():
            flash('Esta obra já está cadastrada na grade de leituras.', 'warning')
        else:
            # Atribuir o usuario_id a um usuário do projeto (por exemplo, o primeiro usuário do projeto)
            usuario_id = projeto.usuarios[0].id  # Isso vai atribuir o ID do primeiro usuário do projeto à grade

            nova_grade = GradeLeitura(projeto_id=projeto.id, obra_id=obra.id, usuario_id=usuario_id)
            db.session.add(nova_grade)
            db.session.commit()

            # Enviar notificações
            for usuario in projeto.usuarios:
                notificacao = Notificacao(
                    mensagem=f"Nova grade de leitura foi lançada para o projeto: {projeto.nome} com a obra '{obra.titulo}'",
                    usuario_id=usuario.id,
                    data_criacao=datetime.utcnow()
                )
                db.session.add(notificacao)

            db.session.commit()
            flash('Obra adicionada à grade de leituras com sucesso!', 'success')

        return redirect(url_for('cadastrar_grade_leitura', projeto_id=projeto_id))

    return render_template('admin/projetos/cadastrar_grade.html', admin=admin, projeto=projeto, obras_disponiveis=obras_disponiveis)
