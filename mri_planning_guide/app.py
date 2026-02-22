import os, uuid, sqlite3
from functools import wraps
from flask import (Flask, render_template, redirect, url_for, request,
                   session, flash, send_from_directory, g, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY']    = 'mri-cuf-guide-2024-secret'
app.config['DATABASE']      = os.path.join(BASE_DIR, 'mri_guide.db')
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = generate_password_hash('mri@admin2024')

# ── DB helpers ──────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_): db = g.pop('db', None); db and db.close()

def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv  = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def execute(sql, args=()):
    db = get_db(); cur = db.execute(sql, args); db.commit(); return cur.lastrowid

def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.executescript('''
        CREATE TABLE IF NOT EXISTS category (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            region_key TEXT NOT NULL DEFAULT "other",
            color      TEXT NOT NULL DEFAULT "#0071BC"
        );
        CREATE TABLE IF NOT EXISTS exam (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id     INTEGER NOT NULL,
            name            TEXT NOT NULL,
            contrast        TEXT NOT NULL DEFAULT "Sem contraste",
            description     TEXT,
            planes          TEXT,
            technical_notes TEXT,
            FOREIGN KEY (category_id) REFERENCES category(id)
        );
        CREATE TABLE IF NOT EXISTS exam_sequence (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id  INTEGER NOT NULL,
            order_num INTEGER NOT NULL DEFAULT 0,
            name     TEXT NOT NULL,
            FOREIGN KEY (exam_id) REFERENCES exam(id)
        );
        CREATE TABLE IF NOT EXISTS sequence_image (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sequence_id INTEGER NOT NULL,
            filename    TEXT NOT NULL,
            caption     TEXT,
            FOREIGN KEY (sequence_id) REFERENCES exam_sequence(id)
        );
        CREATE TABLE IF NOT EXISTS exam_image (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id  INTEGER NOT NULL,
            filename TEXT NOT NULL,
            caption  TEXT,
            FOREIGN KEY (exam_id) REFERENCES exam(id)
        );
    ''')
    db.commit(); db.close()

def seed_data():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    if db.execute('SELECT COUNT(*) FROM category').fetchone()[0] == 0:
        cats = [
            ('Cabeca e Cranio',    'head',         '#0071BC'),
            ('Pescoco',            'neck',          '#0099CC'),
            ('Coluna Vertebral',   'spine',         '#00557A'),
            ('Membros Superiores', 'upper_limbs',   '#0085D1'),
            ('Membros Inferiores', 'lower_limbs',   '#005A8E'),
            ('Abdomen',            'abdomen',       '#0071BC'),
            ('Pelve',              'pelvis',        '#003F7F'),
            ('Coracao e Torax',    'chest',         '#0059A3'),
        ]
        for c in cats:
            db.execute('INSERT INTO category (name,region_key,color) VALUES (?,?,?)', c)
        db.commit()
        cat_id = db.execute("SELECT id FROM category WHERE region_key='head'").fetchone()['id']
        eid = db.execute('''INSERT INTO exam
            (category_id,name,contrast,description,planes,technical_notes) VALUES (?,?,?,?,?,?)''', (
            cat_id, 'RM de Cranio', 'Com e sem contraste',
            'Avaliacao geral do encefalo para rastreio de lesoes, tumores, AVCs e malformacoes vasculares.',
            'Axial, Sagital, Coronal',
            'Espessura de corte: 5 mm (FOV 22 cm)\nMatriz: 256x256\nAngulacao axial: paralela ao CA-CP\nContraste: Gadolinio 0.1 mmol/kg IV'
        )).lastrowid
        seqs = ['T1 SE Axial','T2 TSE Axial','FLAIR Axial','DWI (b0/b1000) Axial','T2* GRE Axial','T1 SE Sagital','T1 SE Coronal com contraste']
        for i,s in enumerate(seqs):
            db.execute('INSERT INTO exam_sequence (exam_id,order_num,name) VALUES (?,?,?)',(eid,i,s))
        db.commit()
    db.close()

def allowed_file(fn): return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def dec(*a,**k):
        if not session.get('admin_logged_in'):
            flash('Acesso restrito.','error'); return redirect(url_for('admin_login'))
        return f(*a,**k)
    return dec

def save_file(file):
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.',1)[1].lower()
        fname = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        return fname
    return None

# ── Public routes ────────────────────────────────────────────────────────────
@app.route('/')
def index():
    cats = query('SELECT * FROM category')
    cats_data = []
    for cat in cats:
        exams = query('SELECT * FROM exam WHERE category_id=?',(cat['id'],))
        cats_data.append({'cat': dict(cat), 'exams': [dict(e) for e in exams]})
    return render_template('index.html', cats_data=cats_data)

@app.route('/category/<int:category_id>')
def category(category_id):
    cat = query('SELECT * FROM category WHERE id=?',(category_id,),one=True)
    if not cat: return redirect(url_for('index'))
    exams = query('SELECT * FROM exam WHERE category_id=?',(category_id,))
    exams_data = []
    for ex in exams:
        seqs = query('SELECT * FROM exam_sequence WHERE exam_id=? ORDER BY order_num',(ex['id'],))
        imgs = query('SELECT * FROM exam_image WHERE exam_id=?',(ex['id'],))
        exams_data.append({'exam':dict(ex),'sequences':[dict(s) for s in seqs],'images':[dict(i) for i in imgs]})
    return render_template('category.html', category=dict(cat), exams_data=exams_data)

@app.route('/exam/<int:exam_id>')
def exam_detail(exam_id):
    ex = query('SELECT e.*, c.name as cat_name, c.region_key, c.color as cat_color, c.id as cat_id '
               'FROM exam e JOIN category c ON e.category_id=c.id WHERE e.id=?',(exam_id,),one=True)
    if not ex: return redirect(url_for('index'))
    seqs = query('SELECT * FROM exam_sequence WHERE exam_id=? ORDER BY order_num',(exam_id,))
    seqs_with_imgs = []
    for s in seqs:
        imgs = query('SELECT * FROM sequence_image WHERE sequence_id=?',(s['id'],))
        seqs_with_imgs.append({'seq':dict(s),'images':[dict(i) for i in imgs]})
    exam_imgs = query('SELECT * FROM exam_image WHERE exam_id=?',(exam_id,))
    return render_template('exam.html', exam=dict(ex),
                           sequences=seqs_with_imgs, exam_images=[dict(i) for i in exam_imgs])

@app.route('/uploads/<filename>')
def uploaded_file(filename): return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ── Admin auth ───────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        if (request.form.get('username')==ADMIN_USERNAME and
                check_password_hash(ADMIN_PASSWORD, request.form.get('password',''))):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Credenciais invalidas.','error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in',None); return redirect(url_for('index'))

# ── Admin dashboard ──────────────────────────────────────────────────────────
@app.route('/admin')
@login_required
def admin_dashboard():
    cats = query('SELECT * FROM category')
    cats_data = []
    for cat in cats:
        exams = query('SELECT * FROM exam WHERE category_id=?',(cat['id'],))
        cats_data.append({'cat':dict(cat),'exams':[dict(e) for e in exams]})
    total_exams = query('SELECT COUNT(*) as c FROM exam',one=True)['c']
    return render_template('admin/dashboard.html', cats_data=cats_data,
                           total_cats=len(cats_data), total_exams=total_exams)

# ── Admin categories ─────────────────────────────────────────────────────────
@app.route('/admin/category/new', methods=['GET','POST'])
@login_required
def admin_new_category():
    if request.method=='POST':
        try:
            execute('INSERT INTO category (name,region_key,color) VALUES (?,?,?)',(
                request.form.get('name','').strip(),
                request.form.get('region_key','other'),
                request.form.get('color','#0071BC')))
            flash('Categoria criada!','success'); return redirect(url_for('admin_dashboard'))
        except: flash('Categoria ja existe.','error')
    return render_template('admin/category_form.html', category=None)

@app.route('/admin/category/<int:cat_id>/edit', methods=['GET','POST'])
@login_required
def admin_edit_category(cat_id):
    cat = query('SELECT * FROM category WHERE id=?',(cat_id,),one=True)
    if not cat: return redirect(url_for('admin_dashboard'))
    if request.method=='POST':
        execute('UPDATE category SET name=?,region_key=?,color=? WHERE id=?',(
            request.form.get('name','').strip(),
            request.form.get('region_key','other'),
            request.form.get('color','#0071BC'), cat_id))
        flash('Categoria atualizada!','success'); return redirect(url_for('admin_dashboard'))
    return render_template('admin/category_form.html', category=dict(cat))

@app.route('/admin/category/<int:cat_id>/delete', methods=['POST'])
@login_required
def admin_delete_category(cat_id):
    exams = query('SELECT id FROM exam WHERE category_id=?',(cat_id,))
    for ex in exams:
        _delete_exam_files(ex['id'])
        execute('DELETE FROM exam WHERE id=?',(ex['id'],))
    execute('DELETE FROM category WHERE id=?',(cat_id,))
    flash('Categoria excluida.','info'); return redirect(url_for('admin_dashboard'))

# ── Admin exams ───────────────────────────────────────────────────────────────
@app.route('/admin/exam/new', methods=['GET','POST'])
@login_required
def admin_new_exam():
    cats = query('SELECT * FROM category')
    if request.method=='POST':
        eid = execute('''INSERT INTO exam
            (category_id,name,contrast,description,planes,technical_notes) VALUES (?,?,?,?,?,?)''',(
            request.form.get('category_id'),
            request.form.get('name','').strip(),
            request.form.get('contrast','Sem contraste'),
            request.form.get('description',''),
            request.form.get('planes',''),
            request.form.get('technical_notes','')))
        # Save sequences
        seq_names = [s.strip() for s in request.form.get('sequences','').split('\n') if s.strip()]
        for i,sname in enumerate(seq_names):
            execute('INSERT INTO exam_sequence (exam_id,order_num,name) VALUES (?,?,?)',(eid,i,sname))
        # General exam images
        for f in request.files.getlist('images'):
            fname = save_file(f)
            if fname: execute('INSERT INTO exam_image (exam_id,filename,caption) VALUES (?,?,?)',(eid,fname,''))
        flash('Exame criado!','success'); return redirect(url_for('admin_edit_exam', exam_id=eid))
    return render_template('admin/exam_form.html', exam=None, categories=[dict(c) for c in cats],
                           sequences=[], exam_images=[])

@app.route('/admin/exam/<int:exam_id>/edit', methods=['GET','POST'])
@login_required
def admin_edit_exam(exam_id):
    ex = query('SELECT * FROM exam WHERE id=?',(exam_id,),one=True)
    if not ex: return redirect(url_for('admin_dashboard'))
    cats = query('SELECT * FROM category')
    if request.method=='POST':
        execute('''UPDATE exam SET category_id=?,name=?,contrast=?,description=?,
                   planes=?,technical_notes=? WHERE id=?''',(
            request.form.get('category_id'),
            request.form.get('name','').strip(),
            request.form.get('contrast','Sem contraste'),
            request.form.get('description',''),
            request.form.get('planes',''),
            request.form.get('technical_notes',''), exam_id))
        # Rebuild sequences
        old_seqs = query('SELECT id FROM exam_sequence WHERE exam_id=?',(exam_id,))
        for s in old_seqs:
            imgs = query('SELECT filename FROM sequence_image WHERE sequence_id=?',(s['id'],))
            for img in imgs:
                p = os.path.join(app.config['UPLOAD_FOLDER'], img['filename'])
                if os.path.exists(p): os.remove(p)
            execute('DELETE FROM sequence_image WHERE sequence_id=?',(s['id'],))
        execute('DELETE FROM exam_sequence WHERE exam_id=?',(exam_id,))
        seq_names = [s.strip() for s in request.form.get('sequences','').split('\n') if s.strip()]
        for i,sname in enumerate(seq_names):
            execute('INSERT INTO exam_sequence (exam_id,order_num,name) VALUES (?,?,?)',(exam_id,i,sname))
        # General exam images
        for f in request.files.getlist('images'):
            fname = save_file(f)
            if fname: execute('INSERT INTO exam_image (exam_id,filename,caption) VALUES (?,?,?)',(exam_id,fname,''))
        flash('Exame atualizado!','success')
        return redirect(url_for('admin_edit_exam', exam_id=exam_id))
    seqs = query('SELECT * FROM exam_sequence WHERE exam_id=? ORDER BY order_num',(exam_id,))
    seqs_data = []
    for s in seqs:
        imgs = query('SELECT * FROM sequence_image WHERE sequence_id=?',(s['id'],))
        seqs_data.append({'seq':dict(s),'images':[dict(i) for i in imgs]})
    exam_imgs = query('SELECT * FROM exam_image WHERE exam_id=?',(exam_id,))
    return render_template('admin/exam_form.html', exam=dict(ex),
                           categories=[dict(c) for c in cats],
                           sequences=seqs_data,
                           exam_images=[dict(i) for i in exam_imgs])

@app.route('/admin/exam/<int:exam_id>/delete', methods=['POST'])
@login_required
def admin_delete_exam(exam_id):
    _delete_exam_files(exam_id)
    execute('DELETE FROM exam WHERE id=?',(exam_id,))
    flash('Exame excluido.','info'); return redirect(url_for('admin_dashboard'))

# ── Sequence image upload ────────────────────────────────────────────────────
@app.route('/admin/sequence/<int:seq_id>/upload', methods=['POST'])
@login_required
def admin_upload_seq_image(seq_id):
    seq = query('SELECT * FROM exam_sequence WHERE id=?',(seq_id,),one=True)
    if not seq: return redirect(url_for('admin_dashboard'))
    for f in request.files.getlist('images'):
        fname = save_file(f)
        caption = request.form.get('caption','')
        if fname: execute('INSERT INTO sequence_image (sequence_id,filename,caption) VALUES (?,?,?)',(seq_id,fname,caption))
    flash('Imagem(ns) adicionada(s)!','success')
    return redirect(url_for('admin_edit_exam', exam_id=seq['exam_id']) + '#seq-' + str(seq_id))

@app.route('/admin/sequence_image/<int:img_id>/delete', methods=['POST'])
@login_required
def admin_delete_seq_image(img_id):
    img = query('SELECT si.*, es.exam_id FROM sequence_image si JOIN exam_sequence es ON si.sequence_id=es.id WHERE si.id=?',(img_id,),one=True)
    if img:
        p = os.path.join(app.config['UPLOAD_FOLDER'], img['filename'])
        if os.path.exists(p): os.remove(p)
        execute('DELETE FROM sequence_image WHERE id=?',(img_id,))
        flash('Imagem removida.','info')
        return redirect(url_for('admin_edit_exam', exam_id=img['exam_id']))
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/exam_image/<int:img_id>/delete', methods=['POST'])
@login_required
def admin_delete_exam_image(img_id):
    img = query('SELECT * FROM exam_image WHERE id=?',(img_id,),one=True)
    if img:
        p = os.path.join(app.config['UPLOAD_FOLDER'], img['filename'])
        if os.path.exists(p): os.remove(p)
        execute('DELETE FROM exam_image WHERE id=?',(img_id,))
        flash('Imagem removida.','info')
        return redirect(url_for('admin_edit_exam', exam_id=img['exam_id']))
    return redirect(url_for('admin_dashboard'))

def _delete_exam_files(exam_id):
    seqs = query('SELECT id FROM exam_sequence WHERE exam_id=?',(exam_id,))
    for s in seqs:
        imgs = query('SELECT filename FROM sequence_image WHERE sequence_id=?',(s['id'],))
        for img in imgs:
            p = os.path.join(app.config['UPLOAD_FOLDER'], img['filename'])
            if os.path.exists(p): os.remove(p)
        execute('DELETE FROM sequence_image WHERE sequence_id=?',(s['id'],))
    execute('DELETE FROM exam_sequence WHERE exam_id=?',(exam_id,))
    imgs = query('SELECT filename FROM exam_image WHERE exam_id=?',(exam_id,))
    for img in imgs:
        p = os.path.join(app.config['UPLOAD_FOLDER'], img['filename'])
        if os.path.exists(p): os.remove(p)
    execute('DELETE FROM exam_image WHERE exam_id=?',(exam_id,))

@app.errorhandler(404)
def not_found(_): return render_template('404.html'), 404

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db(); seed_data(); app.run(debug=True)
