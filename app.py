from flask import Flask, render_template, request, redirect, url_for, session, make_response, abort, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired
from io import BytesIO
import pandas as pd
import json
import secrets
import markdown2
import os
import requests
from dotenv import load_dotenv
from flask_table import Table, Col
import time
from brazorobot.grubbstest import grubbstest_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('WTF_CSRF_SECRET_KEY')
valid_password = os.getenv('PASSWORD')

# Register all blueprints
app.register_blueprint(grubbstest_bp, url_prefix='/grubbstest')

class PostForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    site = StringField('Site', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    date = StringField('Date', validators=[DataRequired()])
    image = StringField('Image')
    text = TextAreaField('Text', validators=[DataRequired()])
    video = StringField('Video')
    submit = SubmitField('Submit')

def request_card_data(url):
    # Introduce a delay of 50 milliseconds before making the request
    time.sleep(0.05)

    response = requests.get(url)
    if response.status_code == 200:
        card_data = response.json()
        if 'image_uris' in card_data:
            return card_data
    return None

def get_card_images():
    url = 'https://api.scryfall.com/cards/random'

    # Introduce a delay of 50 milliseconds before making each request
    time.sleep(0.05)
    card_data_1 = request_card_data(url)

    time.sleep(0.05)
    card_data_2 = request_card_data(url)

    if card_data_1 and card_data_2:
        card_images_and_names = [
            (card_data_1['name'], card_data_1['image_uris']['normal'], card_data_1['set_name'], card_data_1['rarity']),
            (card_data_2['name'], card_data_2['image_uris']['normal'], card_data_2['set_name'], card_data_2['rarity'])
        ]
        return card_images_and_names
    return None

@app.route('/', methods=['GET'])
def opening():
    return render_template('opening.html')

@app.route('/magic', methods=['GET'])
def magic():
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)
        magic_blog_posts = [post for post in blog_posts if post['site'] == 'magic']
        selected_magic_blog_posts = list(reversed(magic_blog_posts))[:15]
    return render_template('home.html', blog_posts=selected_magic_blog_posts, site='magic')

@app.route('/ai', methods=['GET'])
def ai():
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)
        ai_blog_posts = [post for post in blog_posts if post['site'] == 'ai']
        selected_ai_blog_posts = list(reversed(ai_blog_posts))[:15]
    return render_template('home.html', blog_posts=selected_ai_blog_posts, site='ai')


@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'selected_images' not in session:
        session['selected_images'] = []
    if 'unselected_images' not in session:
        session['unselected_images'] = []

    if request.method == 'POST':
        selected_cards = request.form.getlist('selected')
        session['selected_images'].extend(
            card for card in session['card_images'] if card[1] in selected_cards
        )
        session['unselected_images'].extend(
            card for card in session['card_images'] if card[1] not in selected_cards
        )
        session.pop('card_images', None)

    if 'card_images' not in session or not session['card_images']:
        # Introduce a delay of 50 milliseconds before making the request to get card images
        time.sleep(0.05)

        card_images = get_card_images()
        if card_images is None:
            # Handle the case when card_images is None
            # You can redirect the user to an error page or display a message
            # Here, we redirect the user back to the home page
            return redirect(url_for('magic'))
        session['card_images'] = card_images

    # Introduce a delay of 50 milliseconds before rendering the template
    time.sleep(0.05)

    return render_template('game.html',
                           card_images=session.get('card_images', []),
                           selected_images=session.get('selected_images', []),
                           unselected_images=session.get('unselected_images', []))


@app.route('/summary')
def summary():
    return render_template('summary.html',
                           selected_images=session.get('selected_images', []),
                           unselected_images=session.get('unselected_images', []))

@app.route('/clear_session', methods=['POST'])
def clear_session():
    session.clear()
    return redirect(url_for('magic'))

@app.route('/download/csv', methods=['GET'])
def download_csv():
    selected_cards = session.get('selected_images', [])
    si = [list(i) for i in selected_cards]
    si.insert(0, ['Card Name', 'Card Image URL', 'Set Name', 'Rarity'])

    si = [",".join(map(str, i)) for i in si]
    output = "\n".join(si)

    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=selected_cards.csv"
    response.headers["Content-type"] = "text/csv"

    return response

@app.route('/download/xls')
def download_xls():
    # Create DataFrame from selected images
    df = pd.DataFrame(session.get('selected_images', []), columns=['Card Name', 'Card Image URL', 'Set Name', 'Rarity'])

    # Create a BytesIO object, save the Excel file there
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    writer.book.close()  # Close the xlsxwriter Workbook object, not the pd.ExcelWriter object
    output.seek(0)

    # Create a Flask response with the Excel file
    resp = make_response(output.read())
    resp.headers["Content-Disposition"] = "attachment; filename=export.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return resp


@app.route('/labeler', methods=['GET', 'POST'])
def labeler():
    categories = ["LOVE THIS CARD", "LOVE THIS ART", "INTERESTING CARD", "BUY THIS CARD",
                  "CRAFT THIS CARD", "GOES IN MY DECK", "BREW WITH IT", "OTHER 1",
                  "OTHER 2", "OTHER 3"]

    if request.method == 'POST':
        if 'card_data' in session:
            rating = request.form.get('rating')
            card_data = session['card_data']
            card_data['rating'] = rating
            card_data['labels'] = []
            for cat in categories:
                if cat in request.form:
                    card_data['labels'].append(cat)
            if 'cards' not in session:
                session['cards'] = []
            session['cards'].append(card_data)
            session.pop('card_data', None)

    if 'card_data' not in session or not session['card_data']:
        # Introduce a delay of 50 milliseconds before making the request to get card data
        time.sleep(0.05)

        card_data = request_card_data('https://api.scryfall.com/cards/random')
        if card_data is None:
            return redirect(url_for('magic'))
        card_data = {
            'name': card_data['name'],
            'image': card_data['image_uris']['normal'],
            'set_name': card_data['set_name'],
            'rarity': card_data['rarity'],
            'labels': [],
            'rating': None
        }
        session['card_data'] = card_data

    # Introduce a delay of 50 milliseconds before rendering the template
    time.sleep(0.05)

    return render_template('labeler.html',
                           card_data=session.get('card_data', {}),
                           cards=session.get('cards', []))



@app.route('/download_2/csv', methods=['GET'])
def download_2_csv():
    cards = session.get('cards', [])
    output = []
    categories = ["LOVE THIS CARD", "LOVE THIS ART", "INTERESTING CARD", "BUY THIS CARD",
                  "CRAFT THIS CARD", "GOES IN MY DECK", "BREW WITH IT", "OTHER 1",
                  "OTHER 2", "OTHER 3", "Rating"]
    output.append(['Card Name', 'Card Image URL', 'Set Name', 'Rarity'] + categories)

    for card in cards:
        row = [card['name'], card['image'], card['set_name'], card['rarity']]
        labels = card.get('labels', [])
        for cat in categories[:-1]:  # Exclude "Rating" from categories for this
            row.append('X' if cat in labels else '')
        row.append(card.get('rating', ''))
        output.append(row)

    output = [",".join(map(str, i)) for i in output]
    output = "\n".join(output)

    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=selected_cards.csv"
    response.headers["Content-type"] = "text/csv"

    return response


@app.route('/download_2/xls')
def download_2_xls():
    cards = session.get('cards', [])
    data = []
    categories = ["LOVE THIS CARD", "LOVE THIS ART", "INTERESTING CARD", "BUY THIS CARD",
                  "CRAFT THIS CARD", "GOES IN MY DECK", "BREW WITH IT", "OTHER 1",
                  "OTHER 2", "OTHER 3", "Rating"]

    for card in cards:
        row = {
            'Card Name': card['name'],
            'Card Image URL': card['image'],
            'Set Name': card['set_name'],
            'Rarity': card['rarity']
        }
        labels = card.get('labels', [])
        for cat in categories[:-1]:  # Exclude "Rating" from categories for this
            row[cat] = 'X' if cat in labels else ''
        row['Rating'] = card.get('rating', '')
        data.append(row)

    # Create DataFrame from selected images
    df = pd.DataFrame(data)

    # Create a BytesIO object, save the Excel file there
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    writer.book.close()  # Close the xlsxwriter Workbook object, not the pd.ExcelWriter object
    output.seek(0)

    # Create a Flask response with the Excel file
    resp = make_response(output.read())
    resp.headers["Content-Disposition"] = "attachment; filename=export.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return resp


@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        if form.password.data != valid_password:
            abort(401)
        new_post = {
            "id": secrets.token_hex(3),
            "title": form.title.data,
            "site": form.site.data,
            "date": form.date.data,
            "image": form.image.data or None,
            "text": markdown2.markdown(form.text.data),
            "video": form.video.data or None,
            "likes": 0,
            "author": form.author.data
        }
        with open('blog_posts.json', 'r+') as file:
            blog_posts = json.load(file)
            blog_posts.append(new_post)
            file.seek(0)
            file.truncate()
            json.dump(blog_posts, file)
        return redirect(url_for(form.site.data))
    return render_template('new_post.html', form=form)

@app.route('/preview', methods=['POST'])
def preview():
    text = request.form.get('text', '')
    html = markdown2.markdown(text)
    return html

@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    # Find the post that matches the post_id
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)
        post = next((post for post in blog_posts if post['id'] == post_id), None)

    if post is None:
        abort(404) # If post with such id doesn't exist, return 404 error

    form = PostForm()

    if form.validate_on_submit():
        if form.password.data != valid_password:
            abort(401)
        # If the form is valid, update the post data
        post['title'] = form.title.data
        post['site'] = form.site.data
        post['date'] = form.date.data
        post['image'] = form.image.data or None
        post['text'] = markdown2.markdown(form.text.data)
        post['video'] = form.video.data or None
        post['author'] = form.author.data
        # Write the updated data back to the file
        with open('blog_posts.json', 'w') as file:
            json.dump(blog_posts, file)
        return redirect(url_for(form.site.data))

    if request.method == 'GET':
        # If the method is GET, populate the form with the current post data
        form.password.data = valid_password
        form.title.data = post['title']
        form.site.data = post['site']
        form.date.data = post['date']
        form.image.data = post['image']
        form.text.data = post['text']
        form.video.data = post['video']
        form.author.data = post['author']

    elif request.method == 'POST':
        print(form.errors) # print form errors when the form is not valid

    return render_template('edit_post.html', form=form)


@app.route('/like/<post_id>', methods=['POST'])
def like_post(post_id):
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)

    post = next((post for post in blog_posts if post['id'] == post_id), None)

    if post is None:
        return jsonify({'error': 'post not found'}), 404

    if 'liked_posts' not in session:
        session['liked_posts'] = []

    if post_id in session['liked_posts']:
        return jsonify({'error': 'already liked'}), 403

    post['likes'] += 1
    session['liked_posts'].append(post_id)
    session.modified = True  # Save the updated session data

    with open('blog_posts.json', 'w') as file:
        json.dump(blog_posts, file)

    return jsonify({'likes': post['likes']})




class LoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.password.data != valid_password:
            abort(401)
        session['logged_in'] = True
        return redirect(url_for('posts'))
    return render_template('login.html', form=form)

# Declare your table
class ItemTable(Table):
    id = Col('Id')
    title = Col('Title')
    date = Col('Date')
    delete = Col('Delete')

# Get some objects
class Item(object):
    def __init__(self, id, title, site, date):
        self.id = id
        self.title = title
        self.site = site
        self.date = date

def get_items():
    with open('blog_posts.json') as f:
        data = json.load(f)
    items = []
    for entry in data:
        id = entry["id"]
        title = entry["title"]
        site = entry["site"]
        date = entry["date"]
        items.append(Item(id, title, site, date))
    return items

@app.route('/posts', methods=['GET'])
def posts():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        items = get_items()
        # Populate the table
        table = ItemTable(items)
        return render_template('posts.html', table=table)

@app.route('/delete_post/<post_id>', methods=['GET'])
def delete_post(post_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        with open('blog_posts.json', 'r') as f:
            data = json.load(f)
        data = [post for post in data if post['id'] != post_id]
        with open('blog_posts.json', 'w') as f:
            json.dump(data, f)
        return redirect(url_for('posts'))

@app.route('/full_post/<post_id>', methods=['GET'])
def full_post(post_id):
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)
    for post in blog_posts:
        if post['id'] == post_id:
            return render_template('full_post.html', post=post)
    abort(404)


if __name__ == '__main__':
    # app.run(debug=False)
    app.run(host="0.0.0.0")
