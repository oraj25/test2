# app.py
import os
import re
from functools import wraps
from urllib.parse import unquote
from flask import Flask, render_template, request, url_for, redirect, session, flash, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dev_local_secret')


# --- Data ---
users = {
    1: {"name": "John Doe", "email": "john@example.com", "member_since": "Jan 2025"},
    2: {"name": "Alice Smith", "email": "alice@example.com", "member_since": "Mar 2024"},
    3: {"name": "Bob Johnson", "email": "bob@example.com", "member_since": "Jan 2025"},
    4: {"name": "Test User", "email": "test@example.com", "member_since": "Jan 2025"},  # default login
    99: {"name": "CTF Master", "email": "ctf@hidden.com", "member_since": "Mar 2024"}
}

books = {
    1: {"title": "To Kill a Mockingbird", "author": "Harper Lee", "genre": "Classic Literature", "desc": "A profound novel about racial injustice and childhood in the American South, told through the eyes of young Scout Finch.", "img": "book1.jpg"},
    2: {"title": "1984", "author": "George Orwell", "genre": "Dystopian", "desc": "A chilling vision of a totalitarian future where surveillance, propaganda, and thought control rule everyday life.", "img": "book2.jpg"},
    3: {"title": "Pride and Prejudice", "author": "Jane Austen", "genre": "Classic Romance", "desc": "A witty and warm-hearted story of manners, misunderstandings, and the slow-burning romance between Elizabeth Bennet and Mr. Darcy.", "img": "book3.jpg"},
    4: {"title": "The Hobbit", "author": "J.R.R. Tolkien", "genre": "Fantasy", "desc": "Bilbo Baggins embarks on an unexpected adventure with dwarves and a wizard, encountering trolls, riddles, and a dragon.", "img": "book4.jpg"},
    5: {"title": "The Catcher in the Rye", "author": "J.D. Salinger", "genre": "Classic", "desc": "A coming-of-age novel following Holden Caulfield as he navigates alienation, identity, and the messy transition to adulthood.", "img": "book5.jpg"},
    6: {"title": "Harry Potter and the Philosopher's Stone", "author": "J.K. Rowling", "genre": "Fantasy", "desc": "The magical origin story of Harry Potter as he discovers Hogwarts, friendship, and the first confrontation with dark forces.", "img": "book6.jpg"},
    7: {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": "Classic", "desc": "A tragic tale of ambition, love, and the American Dream set against the glittering but hollow world of 1920s New York.", "img": "book7.jpg"},
    8: {"title": "Moby-Dick", "author": "Herman Melville", "genre": "Adventure", "desc": "An epic seafaring novel about Captain Ahab's obsessive quest to hunt the white whale, blending adventure with deep philosophical reflection.", "img": "book8.jpg"},
    9: {"title": "Brave New World", "author": "Aldous Huxley", "genre": "Science Fiction", "desc": "A futuristic society built on technological control and manufactured happiness hides a dark truth about individuality and freedom.", "img": "book9.jpg"},
    10: {"title": "The Alchemist", "author": "Paulo Coelho", "genre": "Philosophical Fiction", "desc": "A young shepherd embarks on a mystical journey to find his Personal Legend and discovers the wisdom of following one’s dreams.", "img": "book10.jpg"},
    11: {"title": "The Lord of the Rings: The Fellowship of the Ring", "author": "J.R.R. Tolkien", "genre": "Epic Fantasy", "desc": "The journey begins as Frodo Baggins inherits the One Ring and sets out to destroy it before darkness consumes Middle-earth.", "img": "book11.jpg"},
    12: {"title": "Frankenstein", "author": "Mary Shelley", "genre": "Gothic Horror", "desc": "Victor Frankenstein’s unholy experiment gives life to a creature that forces him to confront the consequences of playing God.", "img": "book12.jpg"},
    13: {"title": "Crime and Punishment", "author": "Fyodor Dostoevsky", "genre": "Psychological Fiction", "desc": "A gripping exploration of morality and guilt as a man wrestles with the aftermath of committing murder.", "img": "book13.jpg"},
    14: {"title": "The Da Vinci Code", "author": "Dan Brown", "genre": "Thriller", "desc": "A symbologist and cryptologist uncover hidden secrets within religious art and ancient mysteries tied to the Holy Grail.", "img": "book14.jpg"},
    15: {"title": "The Hunger Games", "author": "Suzanne Collins", "genre": "Dystopian", "desc": "In a cruel televised contest, Katniss Everdeen fights for survival and becomes a symbol of rebellion against tyranny.", "img": "book15.jpg"},
    16: {"title": "The Girl with the Dragon Tattoo", "author": "Stieg Larsson", "genre": "Mystery Thriller", "desc": "A journalist and a brilliant hacker delve into a decades-old disappearance and uncover a web of corruption and violence.", "img": "book16.jpg"},
    17: {"title": "The Chronicles of Narnia: The Lion, the Witch and the Wardrobe", "author": "C.S. Lewis", "genre": "Fantasy", "desc": "Four children stumble through a wardrobe into a magical world ruled by an evil witch and help the lion Aslan restore peace.", "img": "book17.jpg"},
    18: {"title": "The Shining", "author": "Stephen King", "genre": "Horror", "desc": "A writer’s descent into madness unfolds when he becomes caretaker of a haunted hotel isolated by winter snow.", "img": "book18.jpg"},
    19: {"title": "The Kite Runner", "author": "Khaled Hosseini", "genre": "Drama", "desc": "A moving story of friendship, betrayal, and redemption set against the backdrop of a changing Afghanistan.", "img": "book19.jpg"},
    20: {"title": "Animal Farm", "author": "George Orwell", "genre": "Political Satire", "desc": "A group of farm animals overthrow their human oppressor, only to see their revolution corrupted by power and greed.", "img": "book20.jpg"},
    99: {"title": "Hidden CTF Book", "author": "CTF Master", "genre": "Secret", "desc": "You found the hidden book!", "img": "hidden_book.jpg", "ctf": True}
}


# In-memory reviews store: { book_id: [ { "author": "...", "content": "..." }, ... ] }
reviews_store = {bid: [] for bid in books.keys()}

# Upload folder
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper: login required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

# --- Simulated webshell commands mapping (safe) ---
SIMULATED_CMDS = {
    "cat /opt/flag_shell.txt": lambda: "THM{shell_flag_02}",
    "id": lambda: "uid=1000(ctf_user) gid=1000(ctf_group)",
    "whoami": lambda: "ctf_user"
}

# --- Routes (essential ones shown; keep your existing routes intact) ---
@app.route('/')
@login_required
def index():
    # index page remains login-protected; index_flag only shown when page is framed (client-side)
    index_flag = "THM{clickjack_index_flag_2025}"
    return render_template('index.html', books=books, index_flag=index_flag)


@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '')
    filtered_books = {id: book for id, book in books.items()
                      if query.lower() in book['title'].lower()
                      or query.lower() in book['author'].lower()
                      or query.lower() in book['genre'].lower()}

    # simple WAF simulation: block explicit <script> tags
    if "<script" in query.lower():
        return render_template('search.html', books=filtered_books, query="Blocked: Malicious input detected!", special_message=None)

    # broader event/handler match for CTF trigger (includes common on* handlers and alert)
    if re.search(r'(%3c|<)[a-z0-9]+(.*?(onerror|onmouseover))', query.lower()):
        flash("THM{burp_reflected_xss_flag_2025}", "flag")

    return render_template('search.html', books=filtered_books, query=query, special_message=None)


@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    # Handles both viewing and posting a review (stored XSS intentionally vulnerable for CTF)
    book_id = request.args.get('id')
    if not book_id or not book_id.isdigit() or int(book_id) not in books:
        return "Book not found!", 404
    bid = int(book_id)
    selected_book = books[bid]

    # POST: receive a review and store it unsafely (CTF vulnerability)
    if request.method == 'POST':
        author = request.form.get('author', '').strip() or session.get('user', {}).get('name', 'Anonymous')
        content = request.form.get('review', '').strip()
        # store raw content (no sanitization) to create stored XSS CTF
        reviews_store.setdefault(bid, []).append({"author": author, "content": content})

        # If review contains obvious script patterns, trigger stored-XSS flag
        if re.search(r'<\s*script|onerror=|javascript:', content, re.IGNORECASE):
            flash("THM{stored_xss_success}", "flag")

        return redirect(url_for('book', id=bid))

    # GET: render book page with stored reviews (rendered unsanitized -> vulnerable)
    book_reviews = reviews_store.get(bid, [])
    return render_template('book.html', book=selected_book, reviews=book_reviews)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if email == 'admin@example.com' and password == 'password123':
            session['user'] = {'id': 0, 'name': 'Admin', 'email': email}
            flash("Welcome, Admin! THM{welcome_flag_find_in_source}", "flag")
            return redirect(url_for('index'))

        for uid, u in users.items():
            if u.get('email') == email and password == 'Welcome123':
                session['user'] = {'id': uid, 'name': u.get('name'), 'email': email}
                flash("Login successful. THM{welcome_flag_find_in_source}", "flag")
                return redirect(url_for('index'))

        if re.search(r"('|\"|;|--|\bOR\b|\bor\b|1=1|union\s+select)", email + password, re.IGNORECASE):
            flash("THM{SQLi_successful}", "flag")
            return render_template('login.html')

        return render_template('login.html', error="Login failed. Try again.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
        _captcha = request.form.get('captcha', '')

        if password != confirm:
            flash("Passwords do not match. Please try again.", "error")
            return render_template('register.html', fullname=fullname, email=email)

        if re.search(r"('|\"|;|--|\bor\b|\bOR\b|\b1=1\b|union\s+select)", fullname + email, re.IGNORECASE):
            flash("THM{register_sqli_success}", "flag")
            fake_user = {"name": "SQLi CTF User", "email": email or "SQLiuser@example.com", "member_since": "SQLi 2025"}
            session['user'] = {'id': 'sqli', 'name': fake_user['name'], 'email': fake_user['email']}
            return redirect(url_for('profile'))

        new_user = {"name": fullname or "New User", "email": email}
        session['user'] = {'id': 'reg', 'name': new_user['name'], 'email': new_user['email']}
        flash("Registration successful. Welcome! THM{register_success_flag}", "flag")
        return redirect(url_for('profile'))

    return render_template('register.html')

@app.route('/profile', methods=['GET'])
@login_required
def profile():
    user_id = request.args.get('id')
    special_flag = None

    if user_id and user_id.isdigit():
        uid = int(user_id)
        if uid in users:
            selected_user = users[uid]
            if uid == 99:
                special_flag = "THM{idor_hidden_user}"
            return render_template('profile.html', user=selected_user, special_flag=special_flag)
        else:
            return "User not found!", 404

    current = session.get('user', {})
    sid = current.get('id')
    if isinstance(sid, int) and sid in users:
        selected_user = users[sid]
        if sid == 99:
            special_flag = "THM{idor_hidden_user}"
        return render_template('profile.html', user=selected_user, special_flag=special_flag)

    return render_template('profile.html', user=current, special_flag=special_flag)

@app.route('/upload_profile', methods=['POST'])
@login_required
def upload_profile():
    file = request.files.get('file')
    if file:
        filename = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(save_path)

    current = session.get('user', {})
    sid = current.get('id')
    if isinstance(sid, int) and sid in users:
        selected_user = users[sid]
        return render_template('profile.html', user=selected_user)
    return render_template('profile.html', user=current)

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/exec/<path:filename>', methods=['GET'])
@login_required
def uploads_exec(filename):
    filename = unquote(filename)
    if ".." in filename or filename.startswith("/"):
        return "Invalid filename", 400
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(file_path):
        return "File not found", 404
    cmd = request.args.get('cmd', '')
    cmd = unquote(cmd).strip()
    lower = filename.lower()
    if not ("shell" in lower or lower.endswith(('.php', '.py', '.jsp', '.sh'))):
        return "No shell behavior detected for this file", 403
    if cmd in SIMULATED_CMDS:
        result = SIMULATED_CMDS[cmd]()
        return f"<pre>{result}</pre>", 200, {'Content-Type': 'text/html'}
    else:
        return "Command not allowed or not recognized", 403
# --- Clickjacking admin page (admin must be logged in) ---
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    current = session.get('user')
    if not current or current.get('id') != 0:
        return "Forbidden: admin only", 403

    admin_flag = None
    if request.method == 'POST':
        admin_flag = "THM{clickjack_admin_flag_2025}"
        session['admin_flag_revealed'] = True

    if session.get('admin_flag_revealed'):
        admin_flag = admin_flag or "THM{clickjack_admin_flag_2025}"

    return render_template('admin.html', admin_flag=admin_flag)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
