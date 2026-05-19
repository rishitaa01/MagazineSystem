"""
app.py — Flask Application
Digital Magazine Management System

Routes:
  /                     Dashboard
  /publishers           Publisher CRUD
  /magazines            Magazine CRUD + search
  /magazines/<id>       Magazine detail
  /articles             Article CRUD
  /authors              Author CRUD
  /editors              Editor CRUD
  /subscribers          Subscriber CRUD
  /subscriptions        Subscription CRUD
  /reports              Analytics & charts
  /delete/<table>/<id>  Generic delete
  /edit/<table>/<id>    Edit form (GET) + update (POST)
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify
)
from database import get_db, init_db
from datetime import date
import os

app = Flask(__name__)
app.secret_key = 'magazine_system_secret_key_2025'


@app.context_processor
def inject_now():
    """Make today's date available in all templates for expiry checks."""
    return {'now': date.today().isoformat()}

# ---------------------------------------------------------------------------
# Initialize DB on first request if it doesn't exist
# ---------------------------------------------------------------------------
@app.before_request
def ensure_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'magazine_system.db')
    if not os.path.exists(db_path):
        init_db()


# ===================================================================
#  DASHBOARD
# ===================================================================
@app.route('/')
def index():
    db = get_db()
    stats = {
        'magazines':   db.execute("SELECT COUNT(*) as c FROM MAGAZINE").fetchone()['c'],
        'articles':    db.execute("SELECT COUNT(*) as c FROM ARTICLE").fetchone()['c'],
        'authors':     db.execute("SELECT COUNT(*) as c FROM AUTHOR").fetchone()['c'],
        'editors':     db.execute("SELECT COUNT(*) as c FROM EDITOR").fetchone()['c'],
        'publishers':  db.execute("SELECT COUNT(*) as c FROM PUBLISHER").fetchone()['c'],
        'subscribers': db.execute("SELECT COUNT(*) as c FROM SUBSCRIBER").fetchone()['c'],
    }
    latest_magazines = db.execute(
        "SELECT m.*, p.name as publisher_name FROM MAGAZINE m "
        "LEFT JOIN PUBLISHER p ON m.publisher_id = p.publisher_id "
        "ORDER BY m.p_date DESC LIMIT 5"
    ).fetchall()
    recent_articles = db.execute(
        "SELECT * FROM Article_Details ORDER BY article_date DESC LIMIT 5"
    ).fetchall()
    db.close()
    return render_template('index.html', stats=stats,
                           latest_magazines=latest_magazines,
                           recent_articles=recent_articles)


# ===================================================================
#  PUBLISHERS
# ===================================================================
@app.route('/publishers', methods=['GET', 'POST'])
def publishers():
    db = get_db()
    if request.method == 'POST':
        try:
            db.execute(
                "INSERT INTO PUBLISHER (name, email, phone, address) VALUES (?, ?, ?, ?)",
                (request.form['name'], request.form['email'],
                 request.form['phone'], request.form['address'])
            )
            db.commit()
            flash('Publisher added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('publishers'))

    search = request.args.get('search', '')
    if search:
        rows = db.execute(
            "SELECT * FROM PUBLISHER WHERE name LIKE ? OR email LIKE ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM PUBLISHER").fetchall()
    db.close()
    return render_template('publishers.html', publishers=rows, search=search)


# ===================================================================
#  MAGAZINES
# ===================================================================
@app.route('/magazines', methods=['GET', 'POST'])
def magazines():
    db = get_db()
    if request.method == 'POST':
        try:
            db.execute(
                "INSERT INTO MAGAZINE (title, language, category, p_date, price, publisher_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (request.form['title'], request.form['language'],
                 request.form['category'], request.form['p_date'],
                 request.form['price'], request.form['publisher_id'] or None)
            )
            db.commit()
            flash('Magazine added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('magazines'))

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    query = ("SELECT m.*, p.name as publisher_name FROM MAGAZINE m "
             "LEFT JOIN PUBLISHER p ON m.publisher_id = p.publisher_id WHERE 1=1 ")
    params = []
    if search:
        query += " AND m.title LIKE ? "
        params.append(f'%{search}%')
    if category:
        query += " AND m.category = ? "
        params.append(category)
    query += " ORDER BY m.p_date DESC"
    rows = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM MAGAZINE ORDER BY category").fetchall()
    publishers_list = db.execute("SELECT publisher_id, name FROM PUBLISHER ORDER BY name").fetchall()
    db.close()
    return render_template('magazines.html', magazines=rows, categories=categories,
                           publishers=publishers_list, search=search, category=category)


@app.route('/magazines/<int:mag_id>')
def magazine_detail(mag_id):
    db = get_db()
    magazine = db.execute(
        "SELECT m.*, p.name as publisher_name FROM MAGAZINE m "
        "LEFT JOIN PUBLISHER p ON m.publisher_id = p.publisher_id "
        "WHERE m.mag_id = ?", (mag_id,)
    ).fetchone()
    if not magazine:
        flash('Magazine not found.', 'error')
        db.close()
        return redirect(url_for('magazines'))

    articles = db.execute("SELECT * FROM Article_Details WHERE article_id IN "
                          "(SELECT article_id FROM ARTICLE WHERE mag_id = ?)",
                          (mag_id,)).fetchall()

    # Subscribers for this magazine
    subscribers = db.execute(
        "SELECT s.name, s.email, sub.start_date, sub.end_date "
        "FROM SUBSCRIPTION sub "
        "JOIN SUBSCRIBER s ON sub.subscriber_id = s.subscriber_id "
        "WHERE sub.mag_id = ?", (mag_id,)
    ).fetchall()

    db.close()
    return render_template('magazine_detail.html', magazine=magazine,
                           articles=articles, subscribers=subscribers)


# ===================================================================
#  ARTICLES
# ===================================================================
@app.route('/articles', methods=['GET', 'POST'])
def articles():
    db = get_db()
    if request.method == 'POST':
        try:
            cur = db.execute(
                "INSERT INTO ARTICLE (title, pages, p_date, mag_id) VALUES (?, ?, ?, ?)",
                (request.form['title'], request.form['pages'],
                 request.form['p_date'], request.form['mag_id'])
            )
            article_id = cur.lastrowid

            # Link authors (multi-select)
            author_ids = request.form.getlist('author_ids')
            for aid in author_ids:
                db.execute("INSERT INTO WRITES (author_id, article_id) VALUES (?, ?)",
                           (aid, article_id))

            # Link editor
            editor_id = request.form.get('editor_id')
            if editor_id:
                db.execute("INSERT INTO EDITS (editor_id, article_id) VALUES (?, ?)",
                           (editor_id, article_id))

            db.commit()
            flash('Article added successfully!', 'success')
        except Exception as e:
            db.rollback()
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('articles'))

    search = request.args.get('search', '')
    mag_filter = request.args.get('mag_id', '')
    query = "SELECT * FROM Article_Details WHERE 1=1 "
    params = []
    if search:
        query += " AND (article_title LIKE ? OR author_names LIKE ?) "
        params.extend([f'%{search}%', f'%{search}%'])
    if mag_filter:
        query += " AND article_id IN (SELECT article_id FROM ARTICLE WHERE mag_id = ?) "
        params.append(mag_filter)
    query += " ORDER BY article_date DESC"
    rows = db.execute(query, params).fetchall()

    magazines_list = db.execute("SELECT mag_id, title FROM MAGAZINE ORDER BY title").fetchall()
    authors_list = db.execute("SELECT author_id, name FROM AUTHOR ORDER BY name").fetchall()
    editors_list = db.execute("SELECT editor_id, name FROM EDITOR ORDER BY name").fetchall()
    db.close()
    return render_template('articles.html', articles=rows, magazines=magazines_list,
                           authors=authors_list, editors=editors_list,
                           search=search, mag_filter=mag_filter)


# ===================================================================
#  AUTHORS
# ===================================================================
@app.route('/authors', methods=['GET', 'POST'])
def authors():
    db = get_db()
    if request.method == 'POST':
        try:
            db.execute(
                "INSERT INTO AUTHOR (name, email, phone, specialization) VALUES (?, ?, ?, ?)",
                (request.form['name'], request.form['email'],
                 request.form['phone'], request.form['specialization'])
            )
            db.commit()
            flash('Author added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('authors'))

    search = request.args.get('search', '')
    if search:
        rows = db.execute(
            "SELECT a.*, COUNT(w.article_id) as article_count "
            "FROM AUTHOR a LEFT JOIN WRITES w ON a.author_id = w.author_id "
            "WHERE a.name LIKE ? OR a.specialization LIKE ? "
            "GROUP BY a.author_id ORDER BY a.name",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT a.*, COUNT(w.article_id) as article_count "
            "FROM AUTHOR a LEFT JOIN WRITES w ON a.author_id = w.author_id "
            "GROUP BY a.author_id ORDER BY a.name"
        ).fetchall()
    db.close()
    return render_template('authors.html', authors=rows, search=search)


# ===================================================================
#  EDITORS
# ===================================================================
@app.route('/editors', methods=['GET', 'POST'])
def editors():
    db = get_db()
    if request.method == 'POST':
        try:
            db.execute(
                "INSERT INTO EDITOR (name, email, experience) VALUES (?, ?, ?)",
                (request.form['name'], request.form['email'],
                 request.form['experience'])
            )
            db.commit()
            flash('Editor added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('editors'))

    search = request.args.get('search', '')
    if search:
        rows = db.execute(
            "SELECT e.*, COUNT(ed.article_id) as article_count "
            "FROM EDITOR e LEFT JOIN EDITS ed ON e.editor_id = ed.editor_id "
            "WHERE e.name LIKE ? "
            "GROUP BY e.editor_id ORDER BY e.name",
            (f'%{search}%',)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT e.*, COUNT(ed.article_id) as article_count "
            "FROM EDITOR e LEFT JOIN EDITS ed ON e.editor_id = ed.editor_id "
            "GROUP BY e.editor_id ORDER BY e.name"
        ).fetchall()
    db.close()
    return render_template('editors.html', editors=rows, search=search)


# ===================================================================
#  SUBSCRIBERS
# ===================================================================
@app.route('/subscribers', methods=['GET', 'POST'])
def subscribers():
    db = get_db()
    if request.method == 'POST':
        try:
            db.execute(
                "INSERT INTO SUBSCRIBER (name, email, phone, city, subscription_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (request.form['name'], request.form['email'],
                 request.form['phone'], request.form['city'],
                 request.form['subscription_type'])
            )
            db.commit()
            flash('Subscriber added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('subscribers'))

    search = request.args.get('search', '')
    city = request.args.get('city', '')
    query = ("SELECT s.*, COUNT(sub.subscription_id) as sub_count "
             "FROM SUBSCRIBER s "
             "LEFT JOIN SUBSCRIPTION sub ON s.subscriber_id = sub.subscriber_id "
             "WHERE 1=1 ")
    params = []
    if search:
        query += " AND (s.name LIKE ? OR s.email LIKE ?) "
        params.extend([f'%{search}%', f'%{search}%'])
    if city:
        query += " AND s.city = ? "
        params.append(city)
    query += " GROUP BY s.subscriber_id ORDER BY s.name"
    rows = db.execute(query, params).fetchall()
    cities = db.execute("SELECT DISTINCT city FROM SUBSCRIBER ORDER BY city").fetchall()
    db.close()
    return render_template('subscribers.html', subscribers=rows,
                           cities=cities, search=search, city=city)


# ===================================================================
#  SUBSCRIPTIONS
# ===================================================================
@app.route('/subscriptions', methods=['GET', 'POST'])
def subscriptions():
    db = get_db()
    if request.method == 'POST':
        try:
            db.execute(
                "INSERT INTO SUBSCRIPTION (subscriber_id, mag_id, start_date, end_date) "
                "VALUES (?, ?, ?, ?)",
                (request.form['subscriber_id'], request.form['mag_id'],
                 request.form['start_date'], request.form['end_date'])
            )
            db.commit()
            flash('Subscription added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        db.close()
        return redirect(url_for('subscriptions'))

    rows = db.execute(
        "SELECT sub.*, s.name as subscriber_name, m.title as magazine_title "
        "FROM SUBSCRIPTION sub "
        "JOIN SUBSCRIBER s ON sub.subscriber_id = s.subscriber_id "
        "JOIN MAGAZINE m ON sub.mag_id = m.mag_id "
        "ORDER BY sub.end_date DESC"
    ).fetchall()
    subscribers_list = db.execute("SELECT subscriber_id, name FROM SUBSCRIBER ORDER BY name").fetchall()
    magazines_list = db.execute("SELECT mag_id, title FROM MAGAZINE ORDER BY title").fetchall()
    db.close()
    return render_template('subscriptions.html', subscriptions=rows,
                           subscribers=subscribers_list, magazines=magazines_list)


# ===================================================================
#  REPORTS / ANALYTICS
# ===================================================================
@app.route('/reports')
def reports():
    db = get_db()

    # Articles per magazine (GROUP BY)
    articles_per_mag = db.execute(
        "SELECT m.title, COUNT(a.article_id) as article_count "
        "FROM MAGAZINE m LEFT JOIN ARTICLE a ON m.mag_id = a.mag_id "
        "GROUP BY m.mag_id ORDER BY article_count DESC"
    ).fetchall()

    # Most subscribed magazine
    most_subscribed = db.execute(
        "SELECT m.title, COUNT(sub.subscription_id) as sub_count "
        "FROM MAGAZINE m JOIN SUBSCRIPTION sub ON m.mag_id = sub.mag_id "
        "GROUP BY m.mag_id ORDER BY sub_count DESC LIMIT 1"
    ).fetchone()

    # Average magazine price
    avg_price = db.execute("SELECT AVG(price) as avg_price FROM MAGAZINE").fetchone()

    # Top authors by article count (HAVING)
    top_authors = db.execute(
        "SELECT au.name, COUNT(w.article_id) as article_count "
        "FROM AUTHOR au JOIN WRITES w ON au.author_id = w.author_id "
        "GROUP BY au.author_id HAVING COUNT(w.article_id) >= 1 "
        "ORDER BY article_count DESC"
    ).fetchall()

    # Active subscriptions count
    active_subs = db.execute(
        "SELECT COUNT(*) as c FROM SUBSCRIPTION WHERE end_date >= DATE('now')"
    ).fetchone()['c']

    # Expired subscriptions count
    expired_subs = db.execute(
        "SELECT COUNT(*) as c FROM SUBSCRIPTION WHERE end_date < DATE('now')"
    ).fetchone()['c']

    # Subscription data by month for chart
    sub_by_month = db.execute(
        "SELECT strftime('%Y-%m', start_date) as month, COUNT(*) as count "
        "FROM SUBSCRIPTION GROUP BY month ORDER BY month"
    ).fetchall()

    # Max price magazine
    max_price_mag = db.execute(
        "SELECT title, MAX(price) as max_price FROM MAGAZINE"
    ).fetchone()

    # Article log (trigger demo)
    article_log = db.execute(
        "SELECT * FROM Article_Log ORDER BY action_time DESC LIMIT 10"
    ).fetchall()

    # Article details view
    article_view = db.execute(
        "SELECT * FROM Article_Details LIMIT 10"
    ).fetchall()

    db.close()
    return render_template('reports.html',
                           articles_per_mag=articles_per_mag,
                           most_subscribed=most_subscribed,
                           avg_price=avg_price,
                           top_authors=top_authors,
                           active_subs=active_subs,
                           expired_subs=expired_subs,
                           sub_by_month=sub_by_month,
                           max_price_mag=max_price_mag,
                           article_log=article_log,
                           article_view=article_view)


# ===================================================================
#  GENERIC DELETE
# ===================================================================
@app.route('/delete/<table>/<int:record_id>', methods=['POST'])
def delete_record(table, record_id):
    """Generic delete handler for any entity."""
    allowed = {
        'publisher':    ('PUBLISHER',    'publisher_id'),
        'magazine':     ('MAGAZINE',     'mag_id'),
        'author':       ('AUTHOR',       'author_id'),
        'editor':       ('EDITOR',       'editor_id'),
        'article':      ('ARTICLE',      'article_id'),
        'subscriber':   ('SUBSCRIBER',   'subscriber_id'),
        'subscription': ('SUBSCRIPTION', 'subscription_id'),
    }
    if table not in allowed:
        flash('Invalid table.', 'error')
        return redirect(url_for('index'))

    tbl, pk = allowed[table]
    db = get_db()
    try:
        db.execute(f"DELETE FROM {tbl} WHERE {pk} = ?", (record_id,))
        db.commit()
        flash(f'{table.capitalize()} deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting: {e}', 'error')
    db.close()

    # Redirect back to the list page
    route_map = {
        'publisher': 'publishers', 'magazine': 'magazines',
        'author': 'authors', 'editor': 'editors',
        'article': 'articles', 'subscriber': 'subscribers',
        'subscription': 'subscriptions',
    }
    return redirect(url_for(route_map[table]))


# ===================================================================
#  GENERIC EDIT  (GET = show form, POST = update)
# ===================================================================
@app.route('/edit/<table>/<int:record_id>', methods=['GET', 'POST'])
def edit_record(table, record_id):
    allowed = {
        'publisher':  ('PUBLISHER',   'publisher_id',  ['name','email','phone','address']),
        'magazine':   ('MAGAZINE',    'mag_id',        ['title','language','category','p_date','price','publisher_id']),
        'author':     ('AUTHOR',      'author_id',     ['name','email','phone','specialization']),
        'editor':     ('EDITOR',      'editor_id',     ['name','email','experience']),
        'subscriber': ('SUBSCRIBER',  'subscriber_id', ['name','email','phone','city','subscription_type']),
    }
    if table not in allowed:
        flash('Invalid table.', 'error')
        return redirect(url_for('index'))

    tbl, pk, fields = allowed[table]
    db = get_db()

    if request.method == 'POST':
        try:
            set_clause = ', '.join(f"{f} = ?" for f in fields)
            values = [request.form.get(f, '') for f in fields]
            values.append(record_id)
            db.execute(f"UPDATE {tbl} SET {set_clause} WHERE {pk} = ?", values)
            db.commit()
            flash(f'{table.capitalize()} updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating: {e}', 'error')
        db.close()
        route_map = {
            'publisher': 'publishers', 'magazine': 'magazines',
            'author': 'authors', 'editor': 'editors',
            'subscriber': 'subscribers',
        }
        return redirect(url_for(route_map[table]))

    # GET — fetch record
    record = db.execute(f"SELECT * FROM {tbl} WHERE {pk} = ?", (record_id,)).fetchone()
    extra = {}
    if table == 'magazine':
        extra['publishers'] = db.execute("SELECT publisher_id, name FROM PUBLISHER ORDER BY name").fetchall()
    db.close()

    if not record:
        flash('Record not found.', 'error')
        return redirect(url_for('index'))

    return render_template('edit.html', table=table, record=record,
                           fields=fields, pk=pk, record_id=record_id, **extra)


# ===================================================================
#  RUN
# ===================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
