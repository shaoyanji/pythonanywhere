from flask import Flask, render_template
import os
import csv
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///texts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret'

db = SQLAlchemy(app)

class Text(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    textid = db.Column(db.Integer)
    type = db.Column(db.String(80))
    issued = db.Column(db.Date)
    title = db.Column(db.String(120))
    language = db.Column(db.String(20))
    authors = db.Column(db.String(120))
    subjects = db.Column(db.String(120))
    locc = db.Column(db.String(20))
    bookshelves = db.Column(db.String(120))

@app.route('/texts')
def texts():
    texts = Text.query.all()
    return render_template('texts.html', texts=texts)

@app.route('/text/<int:id>')
def text(id):
    text = Text.query.get_or_404(id)
    return render_template('text.html', text=text)

def create_tables():
    db.create_all()

def import_csv():
    with open('pg_catalog.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header row
        for row in reader:
            try:
                issued_date = datetime.datetime.strptime(row[2], '%Y-%m-%d').date()
            except ValueError:
                issued_date = None
            text = Text(
                textid=row[0],
                type=row[1],
                issued=issued_date,
                title=row[3],
                language=row[4],
                authors=row[5],
                subjects=row[6],
                locc=row[7],
                bookshelves=row[8]
            )
            db.session.add(text)
        db.session.commit()
    return 'CSV data imported successfully'

@app.cli.command('create-tables')
def create_tables_command():
    create_tables()

@app.cli.command('import-csv')
def import_csv_command():
    create_tables()
    import_csv()

@app.route('/')
def index():
    return render_template('index.html')

#if __name__ == '__main__':
#    app.run(debug=True)

