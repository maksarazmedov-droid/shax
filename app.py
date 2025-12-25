from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db_connection():
    return sqlite3.connect('my_data.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS Items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Details (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            item_id INTEGER, info_name TEXT, player_name TEXT,
            goals INTEGER, status TEXT, rank_place INTEGER
        )
    """)
    conn.commit()
    return conn

db_conn = init_db()

@app.route('/')
def index():
    is_admin = request.args.get('admin') == '1'
    search_query = request.args.get('search', '')
    
    # СОРТИРОВКА: 
    # 1. Сначала те, у кого заполнено Место (по возрастанию: 1, 2, 3)
    # 2. Затем по Голам (по убыванию: 10, 9, 8...)
    sql_query = """
    SELECT Items.id, Items.name, Details.info_name, Details.player_name, Details.goals, Details.status, Details.rank_place
    FROM Items 
    LEFT JOIN Details ON Items.id = Details.item_id
    WHERE 1=1
    """
    params = []
    if search_query:
        sql_query += " AND (Items.name LIKE ? OR Details.player_name LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    # Логика: NULL в местах уходит в конец, остальное по порядку, голы — по убыванию
    sql_query += " ORDER BY (Details.rank_place IS NULL), Details.rank_place ASC, Details.goals DESC"
    
    cursor = db_conn.cursor()
    cursor.execute(sql_query, params)
    rows = cursor.fetchall()
    total_goals = sum(row[4] if row[4] else 0 for row in rows)
    
    return render_template('index.html', rows=rows, search=search_query, total_goals=total_goals, is_admin=is_admin)

@app.route('/add', methods=['POST'])
def add_data():
    item_name = request.form.get('item_name')
    if item_name:
        cursor = db_conn.cursor()
        cursor.execute("INSERT INTO Items (name) VALUES (?)", (item_name,))
        item_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO Details (item_id, info_name, player_name, goals, status, rank_place) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, request.form.get('info_name'), request.form.get('player_name'), 
              request.form.get('goals'), request.form.get('status'), request.form.get('rank_place')))
        db_conn.commit()
    # Возвращаем на админку, если добавляли из неё
    return redirect(url_for('index', admin=1 if request.referrer and 'admin=1' in request.referrer else None))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM Items WHERE id = ?",(item_id,))
    cursor.execute("DELETE FROM Details WHERE item_id = ?",(item_id,))
    db_conn.commit()
    return redirect(url_for('index', admin=1))

if __name__ == '__main__':
    app.run(debug=True)
