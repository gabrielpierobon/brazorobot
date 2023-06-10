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

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('WTF_CSRF_SECRET_KEY')
valid_password = os.getenv('PASSWORD')

class PostForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    date = StringField('Date', validators=[DataRequired()])
    image = StringField('Image')
    text = TextAreaField('Text', validators=[DataRequired()])
    video = StringField('Video')
    submit = SubmitField('Submit')

def request_card_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        card_data = response.json()
        if 'image_uris' in card_data:
            return card_data
    return None

def get_card_images():
    url = 'https://api.scryfall.com/cards/random'
    card_data_1 = request_card_data(url)
    card_data_2 = request_card_data(url)

    if card_data_1 and card_data_2:
        card_images_and_names = [
            (card_data_1['name'], card_data_1['image_uris']['normal'], card_data_1['set_name'], card_data_1['rarity']),
            (card_data_2['name'], card_data_2['image_uris']['normal'], card_data_2['set_name'], card_data_2['rarity'])
        ]
        return card_images_and_names
    return None

@app.route('/', methods=['GET'])
def home():
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)
    return render_template('home.html', blog_posts=list(reversed(blog_posts))[:15])

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
        card_images = get_card_images()
        if card_images is None:
            # Handle the case when card_images is None
            # You can redirect the user to an error page or display a message
            # Here, we redirect the user back to the home page
            return redirect(url_for('home'))
        session['card_images'] = card_images

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
    return redirect(url_for('game'))

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

@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        if form.password.data != valid_password:
            abort(401)
        new_post = {
            "id": secrets.token_hex(3),
            "title": form.title.data,
            "date": form.date.data,
            "image": form.image.data or None,
            "text": markdown2.markdown(form.text.data),
            "video": form.video.data or None,
            "likes": 0
        }
        with open('blog_posts.json', 'r+') as file:
            blog_posts = json.load(file)
            blog_posts.append(new_post)
            file.seek(0)
            file.truncate()
            json.dump(blog_posts, file)
        return redirect(url_for('home'))
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
        post['date'] = form.date.data
        post['image'] = form.image.data
        post['text'] = markdown2.markdown(form.text.data)
        post['video'] = form.video.data or None
        # Write the updated data back to the file
        with open('blog_posts.json', 'w') as file:
            json.dump(blog_posts, file)
        return redirect(url_for('home'))

    if request.method == 'GET':
        # If the method is GET, populate the form with the current post data
        form.password.data = valid_password
        form.title.data = post['title']
        form.date.data = post['date']
        form.image.data = post['image']
        form.text.data = post['text']
        form.video.data = post['video']

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
    def __init__(self, id, title, date):
        self.id = id
        self.title = title
        self.date = date

def get_items():
    with open('blog_posts.json') as f:
        data = json.load(f)
    items = []
    for entry in data:
        id = entry["id"]
        title = entry["title"]
        date = entry["date"]
        items.append(Item(id, title, date))
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
    app.run(debug=False)
